import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.mastery import service
from app.modules.mastery.schemas import (
    ConceptMasteryListResponse,
    ConceptMasteryRead,
    FlashcardDueListResponse,
    FlashcardDueRead,
    FlashcardReviewRequest,
    FlashcardReviewResult,
    MisconceptionListResponse,
    MisconceptionRead,
    WeaknessListResponse,
)

router = APIRouter(prefix="/v1/subjects/{subject_id}", tags=["mastery"])

# Domain errors (NotFoundError) are mapped to HTTP responses by the global
# handlers in app.main.


@router.get("/mastery", response_model=ConceptMasteryListResponse)
async def get_subject_mastery(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConceptMasteryListResponse:
    rows = await service.get_subject_mastery(session, user_id=current_user.id, subject_id=subject_id)
    return ConceptMasteryListResponse(items=[ConceptMasteryRead.model_validate(r) for r in rows])


@router.get("/mastery/concepts/{concept_id}", response_model=ConceptMasteryRead)
async def get_concept_mastery(
    subject_id: uuid.UUID,
    concept_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConceptMasteryRead:
    mastery = await service.get_concept_mastery(
        session, user_id=current_user.id, subject_id=subject_id, concept_id=concept_id
    )
    return ConceptMasteryRead.model_validate(mastery)


@router.get("/mastery/weaknesses", response_model=WeaknessListResponse)
async def get_weaknesses(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeaknessListResponse:
    items = await service.get_weaknesses(session, user_id=current_user.id, subject_id=subject_id)
    return WeaknessListResponse(items=items)


@router.get("/mastery/patterns", response_model=MisconceptionListResponse)
async def get_patterns(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MisconceptionListResponse:
    items = await service.list_misconceptions(session, user_id=current_user.id, subject_id=subject_id)
    return MisconceptionListResponse(items=[MisconceptionRead.model_validate(m) for m in items])


@router.get("/flashcards/due", response_model=FlashcardDueListResponse)
async def get_due_flashcards(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlashcardDueListResponse:
    cards = await service.list_due_flashcards(session, user_id=current_user.id, subject_id=subject_id)
    return FlashcardDueListResponse(items=[FlashcardDueRead.model_validate(c) for c in cards])


@router.post(
    "/flashcards/{flashcard_id}/review", response_model=FlashcardReviewResult, status_code=status.HTTP_201_CREATED
)
async def review_flashcard(
    subject_id: uuid.UUID,
    flashcard_id: uuid.UUID,
    payload: FlashcardReviewRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlashcardReviewResult:
    return await service.submit_flashcard_review(
        session,
        user_id=current_user.id,
        subject_id=subject_id,
        flashcard_id=flashcard_id,
        rating=payload.rating,
        response_ms=payload.response_ms,
    )
