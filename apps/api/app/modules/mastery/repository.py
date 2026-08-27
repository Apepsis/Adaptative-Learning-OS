import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.curriculum.models import Concept
from app.modules.learn.models import Flashcard
from app.modules.mastery.models import (
    ConceptMastery,
    FlashcardReview,
    MasteryEvent,
    Misconception,
    ReviewState,
)
from app.modules.practice.models import Attempt, AttemptError, Question


class MasteryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- concept mastery ---

    async def get_concept_mastery(self, user_id: uuid.UUID, concept_id: uuid.UUID) -> ConceptMastery | None:
        result = await self._session.execute(
            select(ConceptMastery).where(
                ConceptMastery.user_id == user_id, ConceptMastery.concept_id == concept_id
            )
        )
        return result.scalar_one_or_none()

    async def list_mastery_for_subject(self, user_id: uuid.UUID, subject_id: uuid.UUID) -> list[ConceptMastery]:
        result = await self._session.execute(
            select(ConceptMastery)
            .join(Concept, ConceptMastery.concept_id == Concept.id)
            .where(ConceptMastery.user_id == user_id, Concept.subject_id == subject_id)
        )
        return list(result.scalars().all())

    async def create_mastery(self, mastery: ConceptMastery) -> ConceptMastery:
        self._session.add(mastery)
        await self._session.flush()
        return mastery

    async def add_mastery_event(self, event: MasteryEvent) -> None:
        self._session.add(event)
        await self._session.flush()

    async def list_attempts_for_concept(self, user_id: uuid.UUID, concept_id: uuid.UUID) -> list[Attempt]:
        result = await self._session.execute(
            select(Attempt)
            .join(Question, Attempt.question_id == Question.id)
            .where(Attempt.user_id == user_id, Question.concept_id == concept_id)
            .order_by(Attempt.created_at)
        )
        return list(result.scalars().all())

    async def get_hint_count_by_question_id(self, question_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not question_ids:
            return {}
        result = await self._session.execute(
            select(Question.id, Question.hints).where(Question.id.in_(question_ids))
        )
        return {qid: len(hints or []) for qid, hints in result.all()}

    # --- misconceptions / error patterns ---

    async def list_error_events_for_concept(
        self, user_id: uuid.UUID, concept_id: uuid.UUID, error_type: str
    ) -> list[tuple[uuid.UUID, datetime]]:
        result = await self._session.execute(
            select(Attempt.question_id, AttemptError.created_at)
            .join(Attempt, AttemptError.attempt_id == Attempt.id)
            .where(
                Attempt.user_id == user_id,
                AttemptError.concept_id == concept_id,
                AttemptError.error_type == error_type,
            )
            .order_by(AttemptError.created_at)
        )
        return [(question_id, created_at) for question_id, created_at in result.all()]

    async def get_misconception(
        self, user_id: uuid.UUID, concept_id: uuid.UUID, error_type: str
    ) -> Misconception | None:
        result = await self._session.execute(
            select(Misconception).where(
                Misconception.user_id == user_id,
                Misconception.concept_id == concept_id,
                Misconception.error_type == error_type,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_misconception(self, misconception: Misconception) -> Misconception:
        self._session.add(misconception)
        await self._session.flush()
        return misconception

    async def list_misconceptions_for_subject(self, user_id: uuid.UUID, subject_id: uuid.UUID) -> list[Misconception]:
        result = await self._session.execute(
            select(Misconception)
            .join(Concept, Misconception.concept_id == Concept.id)
            .where(Misconception.user_id == user_id, Concept.subject_id == subject_id)
            .order_by(Misconception.last_seen_at.desc())
        )
        return list(result.scalars().all())

    # --- FSRS review state ---

    async def get_review_state(self, flashcard_id: uuid.UUID) -> ReviewState | None:
        result = await self._session.execute(select(ReviewState).where(ReviewState.flashcard_id == flashcard_id))
        return result.scalar_one_or_none()

    async def upsert_review_state(self, review_state: ReviewState) -> ReviewState:
        self._session.add(review_state)
        await self._session.flush()
        return review_state

    async def add_flashcard_review(self, review: FlashcardReview) -> None:
        self._session.add(review)
        await self._session.flush()

    async def list_due_flashcards(self, subject_id: uuid.UUID, *, now: datetime, limit: int) -> list[Flashcard]:
        """Due = has a review_state with due <= now, or has never been
        reviewed at all (brand-new card)."""
        result = await self._session.execute(
            select(Flashcard)
            .outerjoin(ReviewState, ReviewState.flashcard_id == Flashcard.id)
            .where(
                Flashcard.subject_id == subject_id,
                (ReviewState.id.is_(None)) | (ReviewState.due <= now),
            )
            .order_by(Flashcard.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())
