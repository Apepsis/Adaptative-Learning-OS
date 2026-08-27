import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotebookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class NotebookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class NotebookListResponse(BaseModel):
    items: list[NotebookRead]
    total: int


class NotebookSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: uuid.UUID
    title: str
    status: str
    added_at: datetime


class NotebookSourceListResponse(BaseModel):
    items: list[NotebookSourceRead]


class AddSourceRequest(BaseModel):
    source_id: uuid.UUID


class NoteCreate(BaseModel):
    title: str = Field(default="Untitled note", max_length=255)
    content: str = ""


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    content: str | None = None


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class NoteListResponse(BaseModel):
    items: list[NoteRead]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatCitation(BaseModel):
    chunk_id: uuid.UUID
    source_id: uuid.UUID
    source_title: str
    page_start: int
    page_end: int


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    citations: list[ChatCitation]
    not_found: bool
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageRead]
