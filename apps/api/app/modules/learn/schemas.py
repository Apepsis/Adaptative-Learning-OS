import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FlashcardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    concept_id: uuid.UUID
    front: str
    back: str
    source_grounded: bool
    created_at: datetime


class FlashcardListResponse(BaseModel):
    items: list[FlashcardRead]
    total: int


class FlashcardCreate(BaseModel):
    concept_id: uuid.UUID
    front: str = Field(min_length=1, max_length=2000)
    back: str = Field(min_length=1, max_length=2000)


class FlashcardUpdate(BaseModel):
    front: str | None = Field(default=None, max_length=2000)
    back: str | None = Field(default=None, max_length=2000)


class GenerateFlashcardsResponse(BaseModel):
    created: int
    skipped_existing: int


class StudyGuideRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_id: uuid.UUID
    content: str
    updated_at: datetime
