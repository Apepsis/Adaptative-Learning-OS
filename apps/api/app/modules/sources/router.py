import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.sources import service
from app.modules.sources.schemas import SourceListResponse, SourceRead, SourceStatusRead
from app.storage.client import StorageClient, get_storage_client

router = APIRouter(prefix="/v1/sources", tags=["sources"])

# Domain errors raised by the service layer (NotFoundError, ConflictError,
# ValidationFailedError, PayloadTooLargeError) are mapped to HTTP responses
# by the global handlers in app.main — routers don't repeat that mapping.


@router.post("/upload", response_model=SourceRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_source(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    subject_id: uuid.UUID | None = Form(default=None),
    source_role: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> SourceRead:
    source = await service.upload_source(
        session,
        storage,
        settings,
        user_id=current_user.id,
        file=file,
        title=title,
        subject_id=subject_id,
        source_role=source_role,
    )
    return SourceRead.model_validate(source)


@router.get("", response_model=SourceListResponse)
async def list_sources(
    subject_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SourceListResponse:
    sources = await service.list_sources(session, user_id=current_user.id, subject_id=subject_id)
    return SourceListResponse(items=[SourceRead.model_validate(s) for s in sources], total=len(sources))


@router.get("/{source_id}", response_model=SourceRead)
async def get_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SourceRead:
    source = await service.get_source(session, user_id=current_user.id, source_id=source_id)
    return SourceRead.model_validate(source)


@router.get("/{source_id}/status", response_model=SourceStatusRead)
async def get_source_status(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SourceStatusRead:
    source = await service.get_source(session, user_id=current_user.id, source_id=source_id)
    return SourceStatusRead.model_validate(source)


@router.post("/{source_id}/reprocess", response_model=SourceRead, status_code=status.HTTP_202_ACCEPTED)
async def reprocess_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SourceRead:
    source = await service.reprocess_source(session, user_id=current_user.id, source_id=source_id)
    return SourceRead.model_validate(source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.delete_source(session, storage, settings, user_id=current_user.id, source_id=source_id)
