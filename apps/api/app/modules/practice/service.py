import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import GenerationProvider
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.modules.curriculum.service import get_concept as get_concept_detail
from app.modules.mastery.service import record_attempt_outcome
from app.modules.practice.grading import grade_mcq, grade_numeric
from app.modules.practice.models import (
    Attempt,
    AttemptError,
    Correctness,
    PracticeSession,
    Question,
    QuestionOrigin,
    VerificationState,
)
from app.modules.practice.repository import PracticeRepository
from app.modules.practice.schemas import (
    GenerateQuestionsRequest,
    PracticeSessionCreate,
    QuestionCreate,
    QuestionOption,
    SubmitAttemptRequest,
)
from app.modules.subjects.repository import SubjectRepository

# --- generation contracts (structured output, per question type) ---


class _GeneratedMCQ(BaseModel):
    stem: str
    options: list[QuestionOption]
    correct_option_id: str
    solution_text: str
    hints: list[str] = []


class _GeneratedMCQBatch(BaseModel):
    questions: list[_GeneratedMCQ]


class _GeneratedNumeric(BaseModel):
    stem: str
    numeric_answer: float
    numeric_tolerance: float
    units: str | None = None
    solution_text: str
    hints: list[str] = []


class _GeneratedNumericBatch(BaseModel):
    questions: list[_GeneratedNumeric]


class _GeneratedShortAnswer(BaseModel):
    stem: str
    sample_answer: str
    solution_text: str
    hints: list[str] = []


class _GeneratedShortAnswerBatch(BaseModel):
    questions: list[_GeneratedShortAnswer]


_ErrorType = Literal[
    "CONCEPTUAL",
    "PREREQUISITE_GAP",
    "ALGEBRA",
    "ARITHMETIC",
    "UNIT",
    "SIGN",
    "VECTOR_COMPONENT",
    "DIAGRAM_INTERPRETATION",
    "FORMULA_RECALL",
    "FORMULA_SELECTION",
    "ASSUMPTION",
    "BOUNDARY_CONDITION",
    "CALCULUS",
    "CARELESS",
    "INCOMPLETE_JUSTIFICATION",
]


class _ErrorClassification(BaseModel):
    error_type: _ErrorType
    explanation: str


class _ShortAnswerGrade(BaseModel):
    correctness: Literal["correct", "partial", "incorrect"]
    score: float
    feedback: str
    error_type: _ErrorType | None = None
    error_explanation: str | None = None


_GENERATION_SYSTEM_INSTRUCTION = """You write practice questions for a student, grounded strictly \
in the evidence excerpts provided below. Do not introduce facts, numbers, or claims the evidence \
doesn't support.

For each question, also provide 1-3 hints ordered from a gentle nudge to a stronger hint — never \
give away the final answer in a hint.

For multiple choice: give exactly 4 options with ids "a", "b", "c", "d". Exactly one must be \
correct. Distractors should reflect plausible misconceptions, not be obviously wrong.

For numeric: give a numeric_answer and a sensible numeric_tolerance for the precision the evidence \
supports (never 0 unless the answer is an exact small integer).

For short answer: give a concise sample_answer a correct response should match in substance."""

_ERROR_CLASSIFICATION_SYSTEM_INSTRUCTION = """You are analyzing why a student's answer to a \
practice question was not fully correct, to help them understand the mistake — not to grade it \
(that's already done).

Given the question, the correct answer, and what the student submitted, classify the error as \
exactly one of: CONCEPTUAL, PREREQUISITE_GAP, ALGEBRA, ARITHMETIC, UNIT, SIGN, VECTOR_COMPONENT, \
DIAGRAM_INTERPRETATION, FORMULA_RECALL, FORMULA_SELECTION, ASSUMPTION, BOUNDARY_CONDITION, \
CALCULUS, CARELESS, INCOMPLETE_JUSTIFICATION.

Give a one-sentence explanation grounded in the actual difference between the correct and \
submitted answers. If nothing in the given information points to a specific cause, use CARELESS \
and say so honestly rather than guessing at a more specific category."""

_SHORT_ANSWER_GRADING_SYSTEM_INSTRUCTION = """You are grading a student's short-answer response \
against a reference answer. Judge substance, not exact wording.

correctness: "correct" if it captures the key idea(s) of the reference answer, "partial" if it's \
on the right track but missing something material or partly wrong, "incorrect" otherwise.
score: 1.0 for correct, a value in (0, 1) for partial reflecting how much was right, 0.0 for \
incorrect.
feedback: one or two sentences, specific to what was right or missing.
If correctness is not "correct", also classify error_type as one of: CONCEPTUAL, \
PREREQUISITE_GAP, ALGEBRA, ARITHMETIC, UNIT, SIGN, VECTOR_COMPONENT, DIAGRAM_INTERPRETATION, \
FORMULA_RECALL, FORMULA_SELECTION, ASSUMPTION, BOUNDARY_CONDITION, CALCULUS, CARELESS, \
INCOMPLETE_JUSTIFICATION, with a one-sentence error_explanation. Leave both null if correct."""


async def _verify_subject(session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID) -> None:
    subject = await SubjectRepository(session).get_by_id_for_user(subject_id, user_id)
    if subject is None:
        raise NotFoundError(f"Subject {subject_id} not found")


# --- question bank ---


async def create_question(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, data: QuestionCreate
) -> Question:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    _validate_question_shape(
        question_type=data.question_type,
        options=data.options,
        correct_option_id=data.correct_option_id,
        numeric_answer=data.numeric_answer,
        sample_answer=data.sample_answer,
    )
    question = Question(
        subject_id=subject_id,
        concept_id=data.concept_id,
        origin=QuestionOrigin.USER.value,
        question_type=data.question_type,
        stem=data.stem,
        options=[o.model_dump() for o in data.options] if data.options else None,
        correct_option_id=data.correct_option_id,
        numeric_answer=data.numeric_answer,
        numeric_tolerance=data.numeric_tolerance,
        units=data.units,
        sample_answer=data.sample_answer,
        hints=data.hints,
        solution_text=data.solution_text,
        verification_state=VerificationState.VERIFIED.value,
    )
    question = await PracticeRepository(session).create_question(question)
    await session.commit()
    return question


def _validate_question_shape(
    *,
    question_type: str,
    options: list[QuestionOption] | None,
    correct_option_id: str | None,
    numeric_answer: float | None,
    sample_answer: str | None,
) -> None:
    if question_type == "mcq":
        if not options or len(options) < 2:
            raise ValidationFailedError("MCQ questions need at least 2 options")
        option_ids = {o.id for o in options}
        if len(option_ids) != len(options):
            raise ValidationFailedError("MCQ option ids must be unique")
        if correct_option_id not in option_ids:
            raise ValidationFailedError("correct_option_id must match one of the given options")
    elif question_type == "numeric":
        if numeric_answer is None:
            raise ValidationFailedError("Numeric questions need numeric_answer")
    elif question_type == "short_answer" and not sample_answer:
        raise ValidationFailedError("Short-answer questions need sample_answer")


async def list_questions(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID
) -> list[Question]:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    return await PracticeRepository(session).list_questions(subject_id)


def _is_structurally_valid_mcq(item: _GeneratedMCQ) -> bool:
    option_ids = {o.id for o in item.options}
    return len(item.options) >= 2 and len(option_ids) == len(item.options) and item.correct_option_id in option_ids


def _is_structurally_valid_numeric(item: _GeneratedNumeric) -> bool:
    return item.numeric_tolerance >= 0


async def generate_questions(
    session: AsyncSession,
    generation_provider: GenerationProvider,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    subject_id: uuid.UUID,
    data: GenerateQuestionsRequest,
) -> list[Question]:
    """Generation is grounded in one concept's evidence and gets a
    structural-validity check (options well-formed, tolerance non-negative,
    a sample answer present) before being marked VERIFIED — not the full
    independent-solver verification blueprint section 13.6 describes for
    STEM types, which needs a solver this phase doesn't build. Anything
    that fails the structural check is persisted as QUARANTINED rather
    than silently dropped, and excluded from practice session selection.
    """
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    concept, _outgoing, _incoming, evidence = await get_concept_detail(
        session, user_id=user_id, subject_id=subject_id, concept_id=data.concept_id
    )
    if not evidence:
        raise ValidationFailedError(
            "This concept has no source evidence to ground questions in yet."
        )

    evidence_text = "\n".join(f"[{i}] {e.text}" for i, e in enumerate(evidence))
    user_turn = (
        f"Concept: {concept.canonical_name}\nDefinition: {concept.definition or '(none)'}\n\n"
        f"Evidence:\n{evidence_text}\n\nGenerate {data.count} {data.question_type} question(s)."
    )

    repository = PracticeRepository(session)
    created: list[Question] = []

    if data.question_type == "mcq":
        batch = await generation_provider.generate_structured(
            system_instruction=_GENERATION_SYSTEM_INSTRUCTION,
            user_message=user_turn,
            model=settings.reasoning_model,
            response_schema=_GeneratedMCQBatch,
        )
        for mcq_item in batch.questions:
            valid = _is_structurally_valid_mcq(mcq_item)
            question = await repository.create_question(
                Question(
                    subject_id=subject_id,
                    concept_id=concept.id,
                    origin=QuestionOrigin.GENERATED.value,
                    question_type="mcq",
                    stem=mcq_item.stem,
                    options=[o.model_dump() for o in mcq_item.options],
                    correct_option_id=mcq_item.correct_option_id,
                    hints=mcq_item.hints or None,
                    solution_text=mcq_item.solution_text,
                    verification_state=(
                        VerificationState.VERIFIED.value if valid else VerificationState.QUARANTINED.value
                    ),
                )
            )
            created.append(question)

    elif data.question_type == "numeric":
        numeric_batch = await generation_provider.generate_structured(
            system_instruction=_GENERATION_SYSTEM_INSTRUCTION,
            user_message=user_turn,
            model=settings.reasoning_model,
            response_schema=_GeneratedNumericBatch,
        )
        for numeric_item in numeric_batch.questions:
            valid = _is_structurally_valid_numeric(numeric_item)
            question = await repository.create_question(
                Question(
                    subject_id=subject_id,
                    concept_id=concept.id,
                    origin=QuestionOrigin.GENERATED.value,
                    question_type="numeric",
                    stem=numeric_item.stem,
                    numeric_answer=numeric_item.numeric_answer,
                    numeric_tolerance=numeric_item.numeric_tolerance,
                    units=numeric_item.units,
                    hints=numeric_item.hints or None,
                    solution_text=numeric_item.solution_text,
                    verification_state=(
                        VerificationState.VERIFIED.value if valid else VerificationState.QUARANTINED.value
                    ),
                )
            )
            created.append(question)

    else:  # short_answer
        short_batch = await generation_provider.generate_structured(
            system_instruction=_GENERATION_SYSTEM_INSTRUCTION,
            user_message=user_turn,
            model=settings.reasoning_model,
            response_schema=_GeneratedShortAnswerBatch,
        )
        for short_item in short_batch.questions:
            valid = bool(short_item.sample_answer.strip())
            question = await repository.create_question(
                Question(
                    subject_id=subject_id,
                    concept_id=concept.id,
                    origin=QuestionOrigin.GENERATED.value,
                    question_type="short_answer",
                    stem=short_item.stem,
                    sample_answer=short_item.sample_answer,
                    hints=short_item.hints or None,
                    solution_text=short_item.solution_text,
                    verification_state=(
                        VerificationState.VERIFIED.value if valid else VerificationState.QUARANTINED.value
                    ),
                )
            )
            created.append(question)

    await session.commit()
    return created


async def get_hint(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, question_id: uuid.UUID, index: int
) -> tuple[str | None, int]:
    """Returns (hint_text_or_None_if_index_out_of_range, total_hint_count)."""
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    question = await PracticeRepository(session).get_question(subject_id, question_id)
    if question is None:
        raise NotFoundError(f"Question {question_id} not found")
    hints = question.hints or []
    hint_text = hints[index] if 0 <= index < len(hints) else None
    return hint_text, len(hints)


# --- practice sessions ---


async def create_practice_session(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, data: PracticeSessionCreate
) -> PracticeSession:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = PracticeRepository(session)
    question_ids = await repository.pick_question_ids_for_session(
        subject_id, data.concept_ids, data.question_count
    )
    if not question_ids:
        raise ValidationFailedError(
            "No questions available for this subject/selection yet. Generate or add some first."
        )
    practice_session = await repository.create_session(
        PracticeSession(
            user_id=user_id,
            subject_id=subject_id,
            question_ids=[str(qid) for qid in question_ids],
        )
    )
    await session.commit()
    return practice_session


async def get_current(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, session_id: uuid.UUID
) -> tuple[PracticeSession, Question | None]:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = PracticeRepository(session)
    practice_session = await repository.get_session(user_id, session_id)
    if practice_session is None:
        raise NotFoundError(f"Practice session {session_id} not found")

    if practice_session.current_index >= len(practice_session.question_ids):
        return practice_session, None

    question_id = uuid.UUID(practice_session.question_ids[practice_session.current_index])
    question = await repository.get_question(subject_id, question_id)
    return practice_session, question


# --- attempts ---


async def submit_attempt(
    session: AsyncSession,
    generation_provider: GenerationProvider,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    data: SubmitAttemptRequest,
) -> tuple[Attempt, list[AttemptError]]:
    repository = PracticeRepository(session)
    question = await repository.get_question_unscoped(data.question_id)
    if question is None:
        raise NotFoundError(f"Question {data.question_id} not found")
    # Authorization: the question must belong to a subject this user owns.
    await _verify_subject(session, user_id=user_id, subject_id=question.subject_id)

    practice_session = None
    if data.session_id is not None:
        practice_session = await repository.get_session(user_id, data.session_id)
        if practice_session is None:
            raise NotFoundError(f"Practice session {data.session_id} not found")

    correctness: str
    score: float
    feedback: str | None = None
    error_type: str | None = None
    error_explanation: str | None = None

    if data.solution_revealed:
        correctness, score = Correctness.INCORRECT.value, 0.0
    elif question.question_type == "mcq":
        selected = data.raw_answer.get("option_id")
        if not isinstance(selected, str):
            raise ValidationFailedError("raw_answer.option_id is required for MCQ questions")
        correctness, score = grade_mcq(
            correct_option_id=question.correct_option_id or "", selected_option_id=selected
        )
    elif question.question_type == "numeric":
        submitted = data.raw_answer.get("value")
        if not isinstance(submitted, int | float):
            raise ValidationFailedError("raw_answer.value is required for numeric questions")
        correctness, score = grade_numeric(
            correct_value=question.numeric_answer or 0.0,
            tolerance=question.numeric_tolerance or 0.0,
            submitted_value=float(submitted),
        )
    else:  # short_answer
        submitted_text = data.raw_answer.get("text")
        if not isinstance(submitted_text, str) or not submitted_text.strip():
            raise ValidationFailedError("raw_answer.text is required for short-answer questions")
        grade = await generation_provider.generate_structured(
            system_instruction=_SHORT_ANSWER_GRADING_SYSTEM_INSTRUCTION,
            user_message=(
                f"Question: {question.stem}\nReference answer: {question.sample_answer}\n\n"
                f"Student's answer: {submitted_text}"
            ),
            model=settings.fast_model,
            response_schema=_ShortAnswerGrade,
        )
        correctness, score = grade.correctness, grade.score
        feedback = grade.feedback
        error_type, error_explanation = grade.error_type, grade.error_explanation

    attempt = await repository.create_attempt(
        Attempt(
            user_id=user_id,
            question_id=question.id,
            session_id=data.session_id,
            raw_answer=data.raw_answer,
            elapsed_ms=data.elapsed_ms,
            score=score,
            max_score=1.0,
            correctness=correctness,
            hints_used=data.hints_used,
            solution_revealed=data.solution_revealed,
            feedback=feedback,
        )
    )

    errors: list[AttemptError] = []
    if correctness != Correctness.CORRECT.value and not data.solution_revealed:
        if error_type is None:
            # MCQ/numeric: deterministic grading gave no error type yet —
            # ask for one classification call, grounded in the actual
            # correct vs. submitted values (never guessing beyond that).
            classification = await generation_provider.generate_structured(
                system_instruction=_ERROR_CLASSIFICATION_SYSTEM_INSTRUCTION,
                user_message=_format_error_classification_prompt(question, data.raw_answer),
                model=settings.fast_model,
                response_schema=_ErrorClassification,
            )
            error_type, error_explanation = classification.error_type, classification.explanation
        attempt_error = AttemptError(
            attempt_id=attempt.id,
            concept_id=question.concept_id,
            error_type=error_type,
            explanation=error_explanation or "",
        )
        await repository.add_attempt_error(attempt_error)
        errors.append(attempt_error)

    if practice_session is not None:
        practice_session.current_index += 1
        if practice_session.current_index >= len(practice_session.question_ids):
            practice_session.completed_at = datetime.now(UTC)

    await record_attempt_outcome(
        session, user_id=user_id, question=question, attempt=attempt, attempt_errors=errors
    )

    await session.commit()
    return attempt, errors


def _format_error_classification_prompt(question: Question, raw_answer: dict) -> str:
    if question.question_type == "mcq":
        options = {o["id"]: o["text"] for o in (question.options or [])}
        correct = options.get(question.correct_option_id or "", "?")
        submitted = options.get(raw_answer.get("option_id"), "?")
        return f"Question: {question.stem}\nCorrect answer: {correct}\nStudent selected: {submitted}"
    # numeric
    return (
        f"Question: {question.stem}\nCorrect answer: {question.numeric_answer} {question.units or ''}\n"
        f"Student answered: {raw_answer.get('value')}"
    )


async def get_attempt(session: AsyncSession, *, user_id: uuid.UUID, attempt_id: uuid.UUID) -> Attempt:
    repository = PracticeRepository(session)
    attempt = await repository.get_attempt_for_user(user_id, attempt_id)
    if attempt is None:
        raise NotFoundError(f"Attempt {attempt_id} not found")
    return attempt


async def get_attempt_question(session: AsyncSession, *, attempt: Attempt) -> Question:
    """Unscoped by design: the attempt itself was already fetched/created
    under a user-ownership check, so its question_id is trusted."""
    repository = PracticeRepository(session)
    question = await repository.get_question_unscoped(attempt.question_id)
    if question is None:
        raise NotFoundError(f"Question {attempt.question_id} not found")
    return question


async def list_attempt_errors(session: AsyncSession, *, attempt_id: uuid.UUID) -> list[AttemptError]:
    return await PracticeRepository(session).list_attempt_errors(attempt_id)
