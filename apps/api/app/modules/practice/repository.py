import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.practice.models import (
    Attempt,
    AttemptError,
    PracticeSession,
    Question,
    VerificationState,
)


class PracticeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- questions ---

    async def create_question(self, question: Question) -> Question:
        self._session.add(question)
        await self._session.flush()
        return question

    async def get_question(self, subject_id: uuid.UUID, question_id: uuid.UUID) -> Question | None:
        result = await self._session.execute(
            select(Question).where(Question.id == question_id, Question.subject_id == subject_id)
        )
        return result.scalar_one_or_none()

    async def get_question_unscoped(self, question_id: uuid.UUID) -> Question | None:
        """Trusted-context lookup (e.g. grading an attempt already known to
        belong to this user's question) — never reachable directly from a
        router without a subject_id check."""
        return await self._session.get(Question, question_id)

    async def list_questions(self, subject_id: uuid.UUID) -> list[Question]:
        result = await self._session.execute(
            select(Question).where(Question.subject_id == subject_id).order_by(Question.created_at.desc())
        )
        return list(result.scalars().all())

    async def pick_question_ids_for_session(
        self, subject_id: uuid.UUID, concept_ids: list[uuid.UUID] | None, limit: int
    ) -> list[uuid.UUID]:
        # Quarantined (structurally-invalid generated) questions never
        # enter an actual practice session, only user-authored or
        # verified-generated ones (blueprint section 13.4's VERIFIED vs
        # QUARANTINED distinction exists precisely to gate this).
        stmt = select(Question.id).where(
            Question.subject_id == subject_id,
            Question.verification_state == VerificationState.VERIFIED.value,
        )
        if concept_ids:
            stmt = stmt.where(Question.concept_id.in_(concept_ids))
        result = await self._session.execute(stmt)
        ids = list(result.scalars().all())
        random.shuffle(ids)
        return ids[:limit]

    # --- practice sessions ---

    async def create_session(self, practice_session: PracticeSession) -> PracticeSession:
        self._session.add(practice_session)
        await self._session.flush()
        return practice_session

    async def get_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> PracticeSession | None:
        result = await self._session.execute(
            select(PracticeSession).where(
                PracticeSession.id == session_id, PracticeSession.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    # --- attempts ---

    async def create_attempt(self, attempt: Attempt) -> Attempt:
        self._session.add(attempt)
        await self._session.flush()
        return attempt

    async def get_attempt_for_user(self, user_id: uuid.UUID, attempt_id: uuid.UUID) -> Attempt | None:
        result = await self._session.execute(
            select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def add_attempt_error(self, attempt_error: AttemptError) -> None:
        self._session.add(attempt_error)
        await self._session.flush()

    async def list_attempt_errors(self, attempt_id: uuid.UUID) -> list[AttemptError]:
        result = await self._session.execute(
            select(AttemptError).where(AttemptError.attempt_id == attempt_id)
        )
        return list(result.scalars().all())
