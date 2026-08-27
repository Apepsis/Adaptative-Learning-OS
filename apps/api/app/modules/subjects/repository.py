import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subjects.models import Subject


class SubjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, subject: Subject) -> Subject:
        self._session.add(subject)
        await self._session.flush()
        return subject

    async def get_by_id_for_user(self, subject_id: uuid.UUID, user_id: uuid.UUID) -> Subject | None:
        result = await self._session.execute(
            select(Subject).where(Subject.id == subject_id, Subject.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def slug_exists_for_user(self, slug: str, user_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(Subject).where(
                Subject.user_id == user_id, Subject.slug == slug
            )
        )
        return (result.scalar_one() or 0) > 0

    async def list_for_user(self, user_id: uuid.UUID) -> list[Subject]:
        result = await self._session.execute(
            select(Subject).where(Subject.user_id == user_id).order_by(Subject.created_at.desc())
        )
        return list(result.scalars().all())
