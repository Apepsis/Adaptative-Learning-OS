import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    subject_type: str | None = None
    description: str | None = None
    color_token: str | None = None


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    subject_type: str | None
    color_token: str | None
    created_at: datetime


class SubjectListResponse(BaseModel):
    items: list[SubjectRead]
    total: int
