import asyncio
import uuid

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.embeddings.factory import get_embedding_provider
from app.core.config import get_settings
from app.modules.ingestion.parsers.pypdf_parser import PyPdfParser
from app.modules.ingestion.service import ingest_source
from app.storage.client import get_storage_client
from app.workers.celery_app import celery_app

logger = structlog.get_logger("worker.ingestion")


async def _run(source_id: str) -> None:
    settings = get_settings()
    # A fresh engine per task run: the Celery worker process is not the
    # FastAPI event loop, so the app-wide async engine singleton (bound to
    # that loop) cannot be reused here safely.
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with session_factory() as session:
            await ingest_source(
                session,
                get_storage_client(),
                settings,
                PyPdfParser(),
                get_embedding_provider(),
                source_id=uuid.UUID(source_id),
            )
    finally:
        await engine.dispose()


@celery_app.task(name="ingestion.ingest_source", bind=True, max_retries=2, default_retry_delay=30)
def ingest_source_task(self, source_id: str) -> None:
    """Runs the real ingestion pipeline (blueprint section 8): parse,
    chunk, embed, index. Scoped to native-text PDF for this slice — other
    types are marked UNSUPPORTED, not retried."""
    logger.info("ingest_source.received", source_id=source_id)
    try:
        asyncio.run(_run(source_id))
    except Exception as exc:
        logger.warning("ingest_source.retrying", source_id=source_id, attempt=self.request.retries)
        raise self.retry(exc=exc) from exc
    logger.info("ingest_source.done", source_id=source_id)
