import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import GenerationProvider
from app.ai.providers.factory import get_generation_provider
from app.core.config import Settings, get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.practice import service
from app.modules.practice.models import Question
from app.modules.practice.schemas import (
    AttemptErrorRead,
    AttemptResult,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    HintResponse,
    PracticeSessionCreate,
    PracticeSessionCurrent,
    PracticeSessionRead,
    QuestionCreate,
    QuestionListResponse,
    QuestionOption,
    QuestionPracticeView,
    QuestionRead,
    SubmitAttemptRequest,
)

subject_router = APIRouter(prefix="/v1/subjects/{subject_id}", tags=["practice"])
attempts_router = APIRouter(prefix="/v1/attempts", tags=["practice"])

# Domain errors (NotFoundError, ValidationFailedError, AIProviderError) are
# mapped to HTTP responses by the global handlers in app.main.


def _to_practice_view(question: Question) -> QuestionPracticeView:
    return QuestionPracticeView(
        id=question.id,
        question_type=question.question_type,
        stem=question.stem,
        options=(
            [QuestionOption(**o) for o in question.options] if question.question_type == "mcq" and question.options else None
        ),
        units=question.units,
        hint_count=len(question.hints or []),
    )


@subject_router.post("/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
async def create_question(
    subject_id: uuid.UUID,
    payload: QuestionCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuestionRead:
    question = await service.create_question(
        session, user_id=current_user.id, subject_id=subject_id, data=payload
    )
    return QuestionRead.model_validate(question)


@subject_router.get("/questions", response_model=QuestionListResponse)
async def list_questions(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuestionListResponse:
    questions = await service.list_questions(session, user_id=current_user.id, subject_id=subject_id)
    return QuestionListResponse(
        items=[QuestionRead.model_validate(q) for q in questions], total=len(questions)
    )


@subject_router.post(
    "/questions/generate", response_model=GenerateQuestionsResponse, status_code=status.HTTP_201_CREATED
)
async def generate_questions(
    subject_id: uuid.UUID,
    payload: GenerateQuestionsRequest,
    session: AsyncSession = Depends(get_db),
    generation_provider: GenerationProvider = Depends(get_generation_provider),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> GenerateQuestionsResponse:
    questions = await service.generate_questions(
        session, generation_provider, settings, user_id=current_user.id, subject_id=subject_id, data=payload
    )
    return GenerateQuestionsResponse(items=[QuestionRead.model_validate(q) for q in questions])


@subject_router.get("/questions/{question_id}/hints/{index}", response_model=HintResponse)
async def get_hint(
    subject_id: uuid.UUID,
    question_id: uuid.UUID,
    index: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HintResponse:
    hint_text, total = await service.get_hint(
        session, user_id=current_user.id, subject_id=subject_id, question_id=question_id, index=index
    )
    return HintResponse(hint_text=hint_text, hints_used=index + 1, hints_remaining=max(total - index - 1, 0))


@subject_router.post(
    "/practice/sessions", response_model=PracticeSessionCurrent, status_code=status.HTTP_201_CREATED
)
async def create_practice_session(
    subject_id: uuid.UUID,
    payload: PracticeSessionCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PracticeSessionCurrent:
    practice_session = await service.create_practice_session(
        session, user_id=current_user.id, subject_id=subject_id, data=payload
    )
    _, question = await service.get_current(
        session, user_id=current_user.id, subject_id=subject_id, session_id=practice_session.id
    )
    return PracticeSessionCurrent(
        session=PracticeSessionRead(
            id=practice_session.id,
            subject_id=practice_session.subject_id,
            total_questions=len(practice_session.question_ids),
            current_index=practice_session.current_index,
            completed_at=practice_session.completed_at,
        ),
        question=_to_practice_view(question) if question else None,
    )


@subject_router.get("/practice/sessions/{session_id}/current", response_model=PracticeSessionCurrent)
async def get_current_question(
    subject_id: uuid.UUID,
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PracticeSessionCurrent:
    practice_session, question = await service.get_current(
        session, user_id=current_user.id, subject_id=subject_id, session_id=session_id
    )
    return PracticeSessionCurrent(
        session=PracticeSessionRead(
            id=practice_session.id,
            subject_id=practice_session.subject_id,
            total_questions=len(practice_session.question_ids),
            current_index=practice_session.current_index,
            completed_at=practice_session.completed_at,
        ),
        question=_to_practice_view(question) if question else None,
    )


@attempts_router.post("", response_model=AttemptResult, status_code=status.HTTP_201_CREATED)
async def submit_attempt(
    payload: SubmitAttemptRequest,
    session: AsyncSession = Depends(get_db),
    generation_provider: GenerationProvider = Depends(get_generation_provider),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> AttemptResult:
    attempt, errors = await service.submit_attempt(
        session, generation_provider, settings, user_id=current_user.id, data=payload
    )
    question = await service.get_attempt_question(session, attempt=attempt)
    return AttemptResult(
        id=attempt.id,
        correctness=attempt.correctness,
        score=attempt.score,
        max_score=attempt.max_score,
        feedback=attempt.feedback,
        correct_option_id=question.correct_option_id,
        numeric_answer=question.numeric_answer,
        sample_answer=question.sample_answer,
        solution_text=question.solution_text,
        errors=[AttemptErrorRead.model_validate(e) for e in errors],
    )


@attempts_router.get("/{attempt_id}", response_model=AttemptResult)
async def get_attempt(
    attempt_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttemptResult:
    attempt = await service.get_attempt(session, user_id=current_user.id, attempt_id=attempt_id)
    question = await service.get_attempt_question(session, attempt=attempt)
    errors = await service.list_attempt_errors(session, attempt_id=attempt.id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question no longer exists")
    return AttemptResult(
        id=attempt.id,
        correctness=attempt.correctness,
        score=attempt.score,
        max_score=attempt.max_score,
        feedback=attempt.feedback,
        correct_option_id=question.correct_option_id,
        numeric_answer=question.numeric_answer,
        sample_answer=question.sample_answer,
        solution_text=question.solution_text,
        errors=[AttemptErrorRead.model_validate(e) for e in errors],
    )
