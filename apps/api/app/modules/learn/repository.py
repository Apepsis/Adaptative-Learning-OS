import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.learn.models import Flashcard, StudyGuide


class LearnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- flashcards ---

    async def create_flashcard(self, flashcard: Flashcard) -> Flashcard:
        self._session.add(flashcard)
        await self._session.flush()
        return flashcard

    async def get_flashcard(self, subject_id: uuid.UUID, flashcard_id: uuid.UUID) -> Flashcard | None:
        result = await self._session.execute(
            select(Flashcard).where(Flashcard.id == flashcard_id, Flashcard.subject_id == subject_id)
        )
        return result.scalar_one_or_none()

    async def list_flashcards(self, subject_id: uuid.UUID) -> list[Flashcard]:
        result = await self._session.execute(
            select(Flashcard).where(Flashcard.subject_id == subject_id).order_by(Flashcard.created_at)
        )
        return list(result.scalars().all())

    async def flashcard_exists_for_concept(self, concept_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(Flashcard).where(Flashcard.concept_id == concept_id)
        )
        return (result.scalar_one() or 0) > 0

    async def delete_flashcard(self, flashcard: Flashcard) -> None:
        await self._session.delete(flashcard)

    # --- study guide ---

    async def get_study_guide(self, subject_id: uuid.UUID) -> StudyGuide | None:
        result = await self._session.execute(select(StudyGuide).where(StudyGuide.subject_id == subject_id))
        return result.scalar_one_or_none()

    async def upsert_study_guide(self, subject_id: uuid.UUID, content: str) -> StudyGuide:
        guide = await self.get_study_guide(subject_id)
        if guide is None:
            guide = StudyGuide(subject_id=subject_id, content=content)
            self._session.add(guide)
        else:
            guide.content = content
        await self._session.flush()
        return guide
