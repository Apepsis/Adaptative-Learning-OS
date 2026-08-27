import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.subjects import service
from app.modules.subjects.schemas import SubjectCreate, SubjectListResponse, SubjectRead

router = APIRouter(prefix="/v1/subjects", tags=["subjects"])

# Domain errors (e.g. NotFoundError) are mapped to HTTP responses by the
# global handlers in app.main.


@router.post("", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubjectRead:
    subject = await service.create_subject(session, user_id=current_user.id, data=payload)
    return SubjectRead.model_validate(subject)


@router.get("", response_model=SubjectListResponse)
async def list_subjects(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubjectListResponse:
    subjects = await service.list_subjects(session, user_id=current_user.id)
    return SubjectListResponse(
        items=[SubjectRead.model_validate(s) for s in subjects], total=len(subjects)
    )


@router.get("/{subject_id}", response_model=SubjectRead)
async def get_subject(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubjectRead:
    subject = await service.get_subject(session, user_id=current_user.id, subject_id=subject_id)
    return SubjectRead.model_validate(subject)
