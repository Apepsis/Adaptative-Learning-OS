import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import GenerationProvider
from app.ai.providers.factory import get_generation_provider
from app.core.config import Settings, get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.curriculum import service
from app.modules.curriculum.schemas import (
    BuildCurriculumResponse,
    ConceptDetailRead,
    ConceptEdgeRead,
    ConceptListResponse,
    ConceptRead,
    ConceptUpdate,
    MergeConceptsRequest,
)
from app.modules.identity.models import User

router = APIRouter(prefix="/v1/subjects/{subject_id}", tags=["curriculum"])

# Domain errors (NotFoundError, ConflictError, ValidationFailedError,
# AIProviderError) are mapped to HTTP responses by the global handlers in
# app.main.


@router.post(
    "/curriculum/build", response_model=BuildCurriculumResponse, status_code=status.HTTP_201_CREATED
)
async def build_curriculum(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    generation_provider: GenerationProvider = Depends(get_generation_provider),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> BuildCurriculumResponse:
    return await service.build_curriculum(
        session, generation_provider, settings, user_id=current_user.id, subject_id=subject_id
    )


@router.get("/concepts", response_model=ConceptListResponse)
async def list_concepts(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConceptListResponse:
    concepts = await service.list_concepts(session, user_id=current_user.id, subject_id=subject_id)
    return ConceptListResponse(items=[ConceptRead.model_validate(c) for c in concepts], total=len(concepts))


@router.get("/concepts/{concept_id}", response_model=ConceptDetailRead)
async def get_concept(
    subject_id: uuid.UUID,
    concept_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConceptDetailRead:
    concept, outgoing, incoming, evidence = await service.get_concept(
        session, user_id=current_user.id, subject_id=subject_id, concept_id=concept_id
    )
    return ConceptDetailRead(
        **ConceptRead.model_validate(concept).model_dump(),
        outgoing_edges=[ConceptEdgeRead.model_validate(e) for e in outgoing],
        incoming_edges=[ConceptEdgeRead.model_validate(e) for e in incoming],
        evidence=evidence,
    )


@router.patch("/concepts/{concept_id}", response_model=ConceptRead)
async def update_concept(
    subject_id: uuid.UUID,
    concept_id: uuid.UUID,
    payload: ConceptUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConceptRead:
    concept = await service.update_concept(
        session, user_id=current_user.id, subject_id=subject_id, concept_id=concept_id, data=payload
    )
    return ConceptRead.model_validate(concept)


@router.delete("/concepts/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_concept(
    subject_id: uuid.UUID,
    concept_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.delete_concept(session, user_id=current_user.id, subject_id=subject_id, concept_id=concept_id)


@router.post("/concepts/{concept_id}/merge", response_model=ConceptRead)
async def merge_concepts(
    subject_id: uuid.UUID,
    concept_id: uuid.UUID,
    payload: MergeConceptsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConceptRead:
    concept = await service.merge_concepts(
        session,
        user_id=current_user.id,
        subject_id=subject_id,
        primary_concept_id=concept_id,
        absorb_concept_id=payload.absorb_concept_id,
    )
    return ConceptRead.model_validate(concept)
