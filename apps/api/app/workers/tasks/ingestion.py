import asyncio
import uuid

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.modules.sources.models import SourceStatus
from app.modules.sources.repository import SourceRepository
from app.workers.celery_app import celery_app

logger = structlog.get_logger("worker.ingestion")


async def _mark_queued(source_id: str) -> None:
    settings = get_settings()
    # A fresh engine per task run: the Celery worker process is not the
    # FastAPI event loop, so the app-wide async engine singleton (bound to
    # that loop) cannot be reused here safely.
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with session_factory() as session:
            repository = SourceRepository(session)
            source = await repository.get_by_id(uuid.UUID(source_id))
            if source is None:
                logger.warning("ingest_source.not_found", source_id=source_id)
                return
            source.status = SourceStatus.QUEUED.value
            await session.commit()
    finally:
        await engine.dispose()


@celery_app.task(name="ingestion.ingest_source_placeholder", bind=True, max_retries=3)
def ingest_source_placeholder(self, source_id: str) -> None:
    """Placeholder for the real ingestion pipeline (blueprint section 8).

    Phase 1 only proves the async plumbing end-to-end: a source is uploaded,
    a task is enqueued, and the task marks it QUEUED. Parsing, OCR,
    chunking, and embedding are Phase 2 work (see docs/architecture/roadmap.md).
    """
    logger.info("ingest_source.received", source_id=source_id)
    asyncio.run(_mark_queued(source_id))
    logger.info("ingest_source.queued", source_id=source_id)
