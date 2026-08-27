import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sources.models import Source


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, source: Source) -> Source:
        self._session.add(source)
        await self._session.flush()
        return source

    async def get_by_id_for_user(self, source_id: uuid.UUID, user_id: uuid.UUID) -> Source | None:
        result = await self._session.execute(
            select(Source).where(Source.id == source_id, Source.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, source_id: uuid.UUID) -> Source | None:
        """Unscoped lookup for trusted worker contexts only (never routers)."""
        return await self._session.get(Source, source_id)

    async def find_duplicate(self, *, user_id: uuid.UUID, sha256: str) -> Source | None:
        result = await self._session.execute(
            select(Source).where(Source.user_id == user_id, Source.sha256 == sha256)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, subject_id: uuid.UUID | None = None
    ) -> list[Source]:
        stmt = select(Source).where(Source.user_id == user_id)
        if subject_id is not None:
            stmt = stmt.where(Source.subject_id == subject_id)
        stmt = stmt.order_by(Source.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, source: Source) -> None:
        await self._session.delete(source)
