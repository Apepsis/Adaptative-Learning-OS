import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import GenerationProvider
from app.ai.providers.factory import get_generation_provider
from app.core.config import Settings, get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.learn import service
from app.modules.learn.schemas import (
    FlashcardCreate,
    FlashcardListResponse,
    FlashcardRead,
    FlashcardUpdate,
    GenerateFlashcardsResponse,
    StudyGuideRead,
)

router = APIRouter(prefix="/v1/subjects/{subject_id}", tags=["learn"])

# Domain errors (NotFoundError, ValidationFailedError, AIProviderError) are
# mapped to HTTP responses by the global handlers in app.main.


@router.post(
    "/flashcards/generate", response_model=GenerateFlashcardsResponse, status_code=status.HTTP_201_CREATED
)
async def generate_flashcards(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateFlashcardsResponse:
    return await service.generate_flashcards(session, user_id=current_user.id, subject_id=subject_id)


@router.get("/flashcards", response_model=FlashcardListResponse)
async def list_flashcards(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlashcardListResponse:
    flashcards = await service.list_flashcards(session, user_id=current_user.id, subject_id=subject_id)
    return FlashcardListResponse(
        items=[FlashcardRead.model_validate(f) for f in flashcards], total=len(flashcards)
    )


@router.post("/flashcards", response_model=FlashcardRead, status_code=status.HTTP_201_CREATED)
async def create_flashcard(
    subject_id: uuid.UUID,
    payload: FlashcardCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlashcardRead:
    flashcard = await service.create_flashcard(
        session, user_id=current_user.id, subject_id=subject_id, data=payload
    )
    return FlashcardRead.model_validate(flashcard)


@router.patch("/flashcards/{flashcard_id}", response_model=FlashcardRead)
async def update_flashcard(
    subject_id: uuid.UUID,
    flashcard_id: uuid.UUID,
    payload: FlashcardUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlashcardRead:
    flashcard = await service.update_flashcard(
        session, user_id=current_user.id, subject_id=subject_id, flashcard_id=flashcard_id, data=payload
    )
    return FlashcardRead.model_validate(flashcard)


@router.delete("/flashcards/{flashcard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flashcard(
    subject_id: uuid.UUID,
    flashcard_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.delete_flashcard(
        session, user_id=current_user.id, subject_id=subject_id, flashcard_id=flashcard_id
    )


@router.post("/study-guide/generate", response_model=StudyGuideRead, status_code=status.HTTP_201_CREATED)
async def generate_study_guide(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    generation_provider: GenerationProvider = Depends(get_generation_provider),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> StudyGuideRead:
    guide = await service.generate_study_guide(
        session, generation_provider, settings, user_id=current_user.id, subject_id=subject_id
    )
    return StudyGuideRead.model_validate(guide)


@router.get("/study-guide", response_model=StudyGuideRead)
async def get_study_guide(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyGuideRead:
    guide = await service.get_study_guide(session, user_id=current_user.id, subject_id=subject_id)
    if guide is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No study guide generated yet for this subject.",
        )
    return StudyGuideRead.model_validate(guide)
