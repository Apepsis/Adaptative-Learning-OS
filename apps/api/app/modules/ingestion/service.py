import asyncio
import tempfile
import uuid
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import Settings
from app.modules.ingestion.chunking import build_chunks, normalize_text
from app.modules.ingestion.parsers.base import DocumentParser
from app.modules.ingestion.repository import IngestionRepository
from app.modules.retrieval.models import Chunk
from app.modules.retrieval.repository import ChunkRepository
from app.modules.sources.models import SourceStatus
from app.modules.sources.repository import SourceRepository
from app.storage.client import StorageClient

logger = structlog.get_logger("ingestion.service")

_SUPPORTED_MIME_TYPES = {"application/pdf"}


async def ingest_source(
    session: AsyncSession,
    storage: StorageClient,
    settings: Settings,
    parser: DocumentParser,
    embedding_provider: EmbeddingProvider,
    *,
    source_id: uuid.UUID,
) -> None:
    """The real pipeline (blueprint section 8), scoped to native-text PDF
    only for this slice: download -> parse -> persist pages/blocks ->
    chunk -> embed -> persist chunks -> READY.

    Unscoped repository lookups here are safe: this runs only in the
    trusted Celery worker context, never reachable from a router.
    """
    source_repository = SourceRepository(session)
    source = await source_repository.get_by_id(source_id)
    if source is None:
        logger.warning("ingestion.source_not_found", source_id=str(source_id))
        return

    if source.mime_type not in _SUPPORTED_MIME_TYPES:
        source.status = SourceStatus.UNSUPPORTED.value
        source.error_message = (
            f"Parsing for '{source.mime_type}' isn't implemented yet — PDF only in this build."
        )
        await session.commit()
        logger.info("ingestion.unsupported_type", source_id=str(source_id), mime_type=source.mime_type)
        return

    source.status = SourceStatus.PARSING.value
    source.error_message = None
    await session.commit()

    try:
        assert source.storage_key, "source reached ingestion without a storage_key"
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_path = Path(tmp_dir) / "original"
            await storage.download_to_file(
                bucket=settings.s3_bucket_originals, key=source.storage_key, destination=str(local_path)
            )
            document = await asyncio.to_thread(parser.parse, local_path, title=source.title)

        ingestion_repository = IngestionRepository(session)
        await ingestion_repository.replace_pages_and_blocks(source_id, document)

        drafts = build_chunks(document)
        chunk_repository = ChunkRepository(session)
        await chunk_repository.delete_for_source(source_id)

        if drafts:
            texts = [draft.text for draft in drafts]
            embeddings = await asyncio.to_thread(embedding_provider.embed_documents, texts)
            chunks = [
                Chunk(
                    source_id=source_id,
                    subject_id=source.subject_id,
                    page_start=draft.page_start,
                    page_end=draft.page_end,
                    heading_path=draft.heading_path,
                    text=draft.text,
                    normalized_text=normalize_text(draft.text),
                    token_count=draft.token_count,
                    language=source.language,
                    embedding=embedding,
                )
                for draft, embedding in zip(drafts, embeddings, strict=True)
            ]
            await chunk_repository.bulk_create(chunks)

        source.status = SourceStatus.READY.value
        source.parser_name = parser.name
        source.parser_version = parser.version
        await session.commit()
        logger.info("ingestion.ready", source_id=str(source_id), chunk_count=len(drafts))

    except Exception as exc:  # noqa: BLE001 - always record the failure on the source
        await session.rollback()
        source = await source_repository.get_by_id(source_id)
        if source is not None:
            source.status = SourceStatus.FAILED.value
            source.error_message = str(exc)[:2000]
            await session.commit()
        logger.exception("ingestion.failed", source_id=str(source_id))
        raise
