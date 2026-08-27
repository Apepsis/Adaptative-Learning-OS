import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.base import EmbeddingProvider
from app.modules.retrieval.models import Chunk
from app.modules.retrieval.ranking import reciprocal_rank_fusion
from app.modules.retrieval.repository import ChunkRepository
from app.modules.retrieval.schemas import SearchResult
from app.modules.sources.repository import SourceRepository


async def hybrid_search(
    session: AsyncSession,
    embedding_provider: EmbeddingProvider,
    *,
    user_id: uuid.UUID,
    query: str,
    subject_id: uuid.UUID | None = None,
    source_ids: list[uuid.UUID] | None = None,
    top_k: int = 8,
) -> list[SearchResult]:
    repository = ChunkRepository(session)

    query_embedding = await asyncio.to_thread(embedding_provider.embed_query, query)

    # Sequential, not asyncio.gather: both queries share one AsyncSession,
    # and a single SQLAlchemy async session/connection cannot run two
    # operations concurrently (it raises InvalidRequestError if you try) —
    # verified directly against real Postgres.
    vector_results = await repository.vector_search(
        query_embedding, user_id=user_id, subject_id=subject_id, source_ids=source_ids
    )
    lexical_results = await repository.lexical_search(
        query, user_id=user_id, subject_id=subject_id, source_ids=source_ids
    )

    chunk_by_id: dict[uuid.UUID, Chunk] = {c.id: c for c in [*vector_results, *lexical_results]}
    fused = reciprocal_rank_fusion(
        [c.id for c in vector_results],
        [c.id for c in lexical_results],
    )

    source_repository = SourceRepository(session)
    results: list[SearchResult] = []
    for chunk_id, score in fused[:top_k]:
        chunk = chunk_by_id[chunk_id]
        source = await source_repository.get_by_id_for_user(chunk.source_id, user_id)
        if source is None:
            continue  # defensive: shouldn't happen, the repository already scopes by user
        results.append(
            SearchResult(
                chunk_id=chunk.id,
                source_id=chunk.source_id,
                source_title=source.title,
                heading_path=chunk.heading_path,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text=chunk.text,
                score=score,
            )
        )
    return results
