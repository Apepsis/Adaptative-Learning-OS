import statistics
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.curriculum.repository import CurriculumRepository
from app.modules.learn.models import Flashcard
from app.modules.learn.repository import LearnRepository
from app.modules.mastery import bkt, patterns, stats
from app.modules.mastery.fsrs_adapter import card_from_state, new_card
from app.modules.mastery.fsrs_adapter import review as fsrs_review
from app.modules.mastery.models import (
    ConceptMastery,
    FlashcardReview,
    MasteryEvent,
    Misconception,
    MisconceptionStatus,
    ReviewState,
)
from app.modules.mastery.repository import MasteryRepository
from app.modules.mastery.schemas import FlashcardReviewResult, WeaknessRead
from app.modules.practice.models import Attempt, AttemptError, Question
from app.modules.subjects.repository import SubjectRepository

_FULLY_CORRECT = 1.0  # score must equal this to count as "correct" for speed_index (16.8)
_LOW_MASTERY_THRESHOLD = 0.5
_MIN_OBSERVATIONS_FOR_WEAKNESS = 2


async def _verify_subject(session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID) -> None:
    subject = await SubjectRepository(session).get_by_id_for_user(subject_id, user_id)
    if subject is None:
        raise NotFoundError(f"Subject {subject_id} not found")


# --- called from practice.service.submit_attempt after grading ---


async def record_attempt_outcome(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    question: Question,
    attempt: Attempt,
    attempt_errors: list[AttemptError],
) -> None:
    """Updates BKT mastery for `question.concept_id` and checks for an
    emerging error pattern. A no-op if the question isn't linked to a
    concept — manually-authored questions can skip that field, and
    nothing here can attribute evidence without knowing which concept it's
    for."""
    if question.concept_id is None:
        return

    repository = MasteryRepository(session)
    mastery = await repository.get_concept_mastery(user_id, question.concept_id)
    if mastery is None:
        mastery = await repository.create_mastery(
            ConceptMastery(user_id=user_id, concept_id=question.concept_id, p_mastery=bkt.BOOTSTRAP_PRIOR_MASTERY)
        )

    params = bkt.BKT_PARAMS_BY_QUESTION_TYPE.get(question.question_type, bkt.BKT_PARAMS_BY_QUESTION_TYPE["mcq"])
    p_before = mastery.p_mastery
    p_after = bkt.update_mastery(p_before, score=attempt.score, params=params)

    history = await repository.list_attempts_for_concept(user_id, question.concept_id)
    hint_counts = await repository.get_hint_count_by_question_id([a.question_id for a in history])
    observations = [
        stats.Observation(
            score=a.score,
            hints_used=a.hints_used,
            hint_count=hint_counts.get(a.question_id, 0),
            elapsed_ms=a.elapsed_ms,
        )
        for a in history
    ]

    prior_correct_elapsed = [
        a.elapsed_ms for a in history if a.elapsed_ms and a.score >= _FULLY_CORRECT and a.id != attempt.id
    ]
    baseline_ms = statistics.median(prior_correct_elapsed) if prior_correct_elapsed else None
    new_speed_index = stats.speed_index(
        baseline_ms, attempt.elapsed_ms, was_fully_correct=attempt.score >= _FULLY_CORRECT
    )

    mastery.p_mastery = p_after
    mastery.recent_accuracy = stats.recent_accuracy(observations)
    mastery.weighted_accuracy = stats.weighted_accuracy(observations)
    mastery.hint_independence = stats.hint_independence(observations)
    mastery.observation_count = len(observations)
    mastery.distinct_question_count = len({a.question_id for a in history})
    mastery.mastery_confidence = stats.mastery_confidence(
        mastery.observation_count, mastery.distinct_question_count
    )
    if new_speed_index is not None:
        mastery.speed_index = new_speed_index
    mastery.last_evidence_at = attempt.created_at

    await repository.add_mastery_event(
        MasteryEvent(
            user_id=user_id,
            concept_id=question.concept_id,
            attempt_id=attempt.id,
            p_before=p_before,
            p_after=p_after,
            score=attempt.score,
        )
    )

    for attempt_error in attempt_errors:
        misconception = await _update_misconception(
            repository, user_id=user_id, concept_id=question.concept_id, error_type=attempt_error.error_type
        )
        if misconception is not None:
            attempt_error.misconception_id = misconception.id


async def _update_misconception(
    repository: MasteryRepository, *, user_id: uuid.UUID, concept_id: uuid.UUID, error_type: str
) -> Misconception | None:
    rows = await repository.list_error_events_for_concept(user_id, concept_id, error_type)
    events = [patterns.ErrorEvent(question_id=question_id, occurred_at=occurred_at) for question_id, occurred_at in rows]
    status = patterns.evaluate_pattern(events, now=datetime.now(UTC))
    if status is None:
        return None

    misconception = await repository.get_misconception(user_id, concept_id, error_type)
    if misconception is None:
        misconception = Misconception(user_id=user_id, concept_id=concept_id, error_type=error_type)
    misconception.status = status
    misconception.event_count = len(events)
    misconception.distinct_question_count = len({e.question_id for e in events})
    return await repository.upsert_misconception(misconception)


# --- reads ---


async def get_subject_mastery(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID
) -> list[ConceptMastery]:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    return await MasteryRepository(session).list_mastery_for_subject(user_id, subject_id)


async def get_concept_mastery(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, concept_id: uuid.UUID
) -> ConceptMastery:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    concept = await CurriculumRepository(session).get_concept(subject_id, concept_id)
    if concept is None:
        raise NotFoundError(f"Concept {concept_id} not found")
    mastery = await MasteryRepository(session).get_concept_mastery(user_id, concept_id)
    if mastery is None:
        raise NotFoundError("No practice evidence for this concept yet.")
    return mastery


async def get_weaknesses(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, limit: int = 10
) -> list[WeaknessRead]:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = MasteryRepository(session)
    mastery_rows = await repository.list_mastery_for_subject(user_id, subject_id)
    misconceptions = await repository.list_misconceptions_for_subject(user_id, subject_id)

    confirmed_by_concept: dict[uuid.UUID, list[str]] = {}
    for misconception in misconceptions:
        if misconception.status == MisconceptionStatus.CONFIRMED.value:
            confirmed_by_concept.setdefault(misconception.concept_id, []).append(misconception.error_type)

    concepts = await CurriculumRepository(session).list_concepts(subject_id)
    concept_by_id = {c.id: c for c in concepts}

    weak: list[tuple[float, WeaknessRead]] = []
    for row in mastery_rows:
        if row.observation_count < _MIN_OBSERVATIONS_FOR_WEAKNESS:
            continue
        concept = concept_by_id.get(row.concept_id)
        if concept is None:
            continue
        error_types = confirmed_by_concept.get(row.concept_id, [])
        if row.p_mastery >= _LOW_MASTERY_THRESHOLD and not error_types:
            continue
        reason = (
            f"Recurring error pattern: {', '.join(error_types)}"
            if error_types
            else f"Mastery {row.p_mastery:.2f} after {row.observation_count} attempts"
        )
        weak.append(
            (
                row.p_mastery,
                WeaknessRead(
                    concept_id=row.concept_id,
                    concept_name=concept.canonical_name,
                    p_mastery=row.p_mastery,
                    mastery_confidence=row.mastery_confidence,
                    reason=reason,
                ),
            )
        )
    weak.sort(key=lambda pair: pair[0])
    return [item for _, item in weak[:limit]]


async def list_misconceptions(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID
) -> list[Misconception]:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    return await MasteryRepository(session).list_misconceptions_for_subject(user_id, subject_id)


# --- FSRS flashcard review ---


async def list_due_flashcards(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, limit: int = 20
) -> list[Flashcard]:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    return await MasteryRepository(session).list_due_flashcards(subject_id, now=datetime.now(UTC), limit=limit)


async def submit_flashcard_review(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    subject_id: uuid.UUID,
    flashcard_id: uuid.UUID,
    rating: str,
    response_ms: int | None,
) -> FlashcardReviewResult:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    flashcard = await LearnRepository(session).get_flashcard(subject_id, flashcard_id)
    if flashcard is None:
        raise NotFoundError(f"Flashcard {flashcard_id} not found")

    repository = MasteryRepository(session)
    review_state = await repository.get_review_state(flashcard_id)
    now = datetime.now(UTC)
    card = (
        new_card()
        if review_state is None
        else card_from_state(
            state=review_state.state,
            step=review_state.step,
            stability=review_state.stability,
            difficulty=review_state.difficulty,
            due=review_state.due,
            last_review=review_state.last_review,
        )
    )

    updated_card, _log = fsrs_review(card, rating, review_datetime=now, response_ms=response_ms)

    if review_state is None:
        review_state = ReviewState(flashcard_id=flashcard_id, due=updated_card.due)
    review_state.state = updated_card.state.value
    review_state.step = updated_card.step
    review_state.stability = updated_card.stability
    review_state.difficulty = updated_card.difficulty
    review_state.due = updated_card.due
    review_state.last_review = updated_card.last_review
    review_state = await repository.upsert_review_state(review_state)

    await repository.add_flashcard_review(
        FlashcardReview(review_state_id=review_state.id, rating=rating, response_ms=response_ms, reviewed_at=now)
    )

    await session.commit()
    return FlashcardReviewResult(
        flashcard_id=flashcard_id,
        state=updated_card.state.name.lower(),
        due=updated_card.due,
        stability=updated_card.stability,
        difficulty=updated_card.difficulty,
    )
