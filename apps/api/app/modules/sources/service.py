import hashlib
import tempfile
import uuid
from typing import BinaryIO

import magic
import structlog
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, PayloadTooLargeError
from app.modules.sources import policies
from app.modules.sources.models import Source, SourceStatus
from app.modules.sources.repository import SourceRepository
from app.storage.client import StorageClient
from app.workers.tasks.ingestion import ingest_source_placeholder

logger = structlog.get_logger("sources.service")

_CHUNK_SIZE = 1024 * 1024  # 1 MiB, streamed from the client
_SNIFF_BYTES = 4096  # enough for libmagic to identify PDF/DOCX/PPTX/images


async def _buffer_and_hash(file: UploadFile, max_bytes: int) -> tuple[BinaryIO, str, int]:
    """Stream the upload to a spooled temp file while hashing it.

    Aborts as soon as the byte limit is crossed, so an oversized upload is
    never fully buffered before being rejected.
    """
    buffer = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024)
    hasher = hashlib.sha256()
    total = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            buffer.close()
            raise PayloadTooLargeError(
                f"Upload exceeds the {max_bytes} byte limit"
            )
        hasher.update(chunk)
        buffer.write(chunk)
    buffer.seek(0)
    return buffer, hasher.hexdigest(), total


async def upload_source(
    session: AsyncSession,
    storage: StorageClient,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    file: UploadFile,
    title: str | None,
    subject_id: uuid.UUID | None,
    source_role: str | None,
) -> Source:
    buffer, sha256, size_bytes = await _buffer_and_hash(file, settings.max_upload_bytes)
    policies.validate_size(size_bytes, settings.max_upload_bytes)

    sniff_bytes = buffer.read(_SNIFF_BYTES)
    buffer.seek(0)
    mime_type = magic.from_buffer(sniff_bytes, mime=True)

    try:
        policies.validate_mime_allowed(mime_type, settings.allowed_upload_mime_types)
        policies.validate_extension_matches_mime(file.filename, mime_type)
        source_type = policies.resolve_source_type(mime_type)

        repository = SourceRepository(session)
        duplicate = await repository.find_duplicate(user_id=user_id, sha256=sha256)
        if duplicate is not None:
            raise ConflictError(f"This file was already uploaded as source {duplicate.id}")

        extension = policies.extension_for_mime(mime_type)
        storage_key = f"users/{user_id}/sources/{uuid.uuid4()}/original{extension}"

        source = Source(
            user_id=user_id,
            subject_id=subject_id,
            type=source_type,
            title=title or file.filename or "Untitled source",
            original_filename=file.filename,
            storage_key=storage_key,
            mime_type=mime_type,
            sha256=sha256,
            size_bytes=size_bytes,
            source_role=source_role,
            status=SourceStatus.UPLOADED.value,
        )

        await storage.upload_fileobj(
            bucket=settings.s3_bucket_originals,
            key=storage_key,
            fileobj=buffer,
            content_type=mime_type,
        )
    finally:
        buffer.close()

    source = await repository.create(source)
    await session.commit()

    ingest_source_placeholder.delay(str(source.id))
    logger.info("source.uploaded", source_id=str(source.id), size_bytes=size_bytes, mime_type=mime_type)
    return source


async def get_source(session: AsyncSession, *, user_id: uuid.UUID, source_id: uuid.UUID) -> Source:
    source = await SourceRepository(session).get_by_id_for_user(source_id, user_id)
    if source is None:
        raise NotFoundError(f"Source {source_id} not found")
    return source


async def list_sources(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID | None = None
) -> list[Source]:
    return await SourceRepository(session).list_for_user(user_id, subject_id=subject_id)


async def reprocess_source(
    session: AsyncSession, *, user_id: uuid.UUID, source_id: uuid.UUID
) -> Source:
    source = await get_source(session, user_id=user_id, source_id=source_id)
    source.status = SourceStatus.UPLOADED.value
    source.error_message = None
    await session.commit()
    ingest_source_placeholder.delay(str(source.id))
    logger.info("source.reprocess_requested", source_id=str(source.id))
    return source


async def delete_source(
    session: AsyncSession,
    storage: StorageClient,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    source_id: uuid.UUID,
) -> None:
    repository = SourceRepository(session)
    source = await repository.get_by_id_for_user(source_id, user_id)
    if source is None:
        raise NotFoundError(f"Source {source_id} not found")
    if source.storage_key:
        await storage.delete_object(bucket=settings.s3_bucket_originals, key=source.storage_key)
    await repository.delete(source)
    await session.commit()
    logger.info("source.deleted", source_id=str(source_id))
