import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID | None
    type: str
    title: str
    original_filename: str | None
    mime_type: str
    size_bytes: int
    status: str
    error_message: str | None
    source_role: str | None
    created_at: datetime
    updated_at: datetime


class SourceStatusRead(BaseModel):
    id: uuid.UUID
    status: str
    error_message: str | None
    updated_at: datetime


class SourceListResponse(BaseModel):
    items: list[SourceRead]
    total: int
