import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.retrieval.models import Chunk
from app.modules.sources.models import Source

_CANDIDATE_LIMIT = 50


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, chunks: list[Chunk]) -> None:
        self._session.add_all(chunks)
        await self._session.flush()

    async def delete_for_source(self, source_id: uuid.UUID) -> None:
        await self._session.execute(delete(Chunk).where(Chunk.source_id == source_id))

    async def get_with_source_title_for_user(
        self, chunk_ids: list[uuid.UUID], *, user_id: uuid.UUID
    ) -> list[tuple[Chunk, str]]:
        """Used to render evidence as readable excerpts (e.g. the curriculum
        module's lesson view), not just bare chunk ids."""
        if not chunk_ids:
            return []
        stmt = (
            select(Chunk, Source.title)
            .join(Source, Source.id == Chunk.source_id)
            .where(Source.user_id == user_id, Chunk.id.in_(chunk_ids))
        )
        result = await self._session.execute(stmt)
        return [(chunk, title) for chunk, title in result.all()]

    def _scoped(self, *, user_id: uuid.UUID, subject_id: uuid.UUID | None, source_ids: list[uuid.UUID] | None):
        stmt = select(Chunk).join(Source, Source.id == Chunk.source_id).where(Source.user_id == user_id)
        if subject_id is not None:
            stmt = stmt.where(Chunk.subject_id == subject_id)
        if source_ids:
            stmt = stmt.where(Chunk.source_id.in_(source_ids))
        return stmt

    async def vector_search(
        self,
        query_embedding: list[float],
        *,
        user_id: uuid.UUID,
        subject_id: uuid.UUID | None = None,
        source_ids: list[uuid.UUID] | None = None,
        limit: int = _CANDIDATE_LIMIT,
    ) -> list[Chunk]:
        stmt = (
            self._scoped(user_id=user_id, subject_id=subject_id, source_ids=source_ids)
            .order_by(Chunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def lexical_search(
        self,
        query_text: str,
        *,
        user_id: uuid.UUID,
        subject_id: uuid.UUID | None = None,
        source_ids: list[uuid.UUID] | None = None,
        limit: int = _CANDIDATE_LIMIT,
    ) -> list[Chunk]:
        tsquery = func.plainto_tsquery("simple", query_text)
        stmt = (
            self._scoped(user_id=user_id, subject_id=subject_id, source_ids=source_ids)
            .where(Chunk.fts.op("@@")(tsquery))
            .order_by(func.ts_rank(Chunk.fts, tsquery).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
