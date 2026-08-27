import uuid

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    subject_id: uuid.UUID | None = None
    source_ids: list[uuid.UUID] | None = None
    top_k: int = Field(default=8, ge=1, le=30)


class SearchResult(BaseModel):
    chunk_id: uuid.UUID
    source_id: uuid.UUID
    source_title: str
    heading_path: list[str]
    page_start: int
    page_end: int
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    not_found: bool
