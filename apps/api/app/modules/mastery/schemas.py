import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConceptMasteryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    concept_id: uuid.UUID
    p_mastery: float
    mastery_confidence: float
    recent_accuracy: float
    weighted_accuracy: float
    transfer_score: float
    hint_independence: float
    speed_index: float | None
    observation_count: int
    distinct_question_count: int
    last_evidence_at: datetime | None


class ConceptMasteryListResponse(BaseModel):
    items: list[ConceptMasteryRead]


class WeaknessRead(BaseModel):
    concept_id: uuid.UUID
    concept_name: str
    p_mastery: float
    mastery_confidence: float
    reason: str


class WeaknessListResponse(BaseModel):
    items: list[WeaknessRead]


class MisconceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    concept_id: uuid.UUID
    error_type: str
    status: str
    event_count: int
    distinct_question_count: int
    first_seen_at: datetime
    last_seen_at: datetime


class MisconceptionListResponse(BaseModel):
    items: list[MisconceptionRead]


class FlashcardDueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    concept_id: uuid.UUID
    front: str
    back: str


class FlashcardDueListResponse(BaseModel):
    items: list[FlashcardDueRead]


class FlashcardReviewRequest(BaseModel):
    rating: str = Field(pattern="^(again|hard|good|easy)$")
    response_ms: int | None = None


class FlashcardReviewResult(BaseModel):
    flashcard_id: uuid.UUID
    state: str
    due: datetime
    stability: float | None
    difficulty: float | None
