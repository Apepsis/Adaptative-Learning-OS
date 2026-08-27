import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConceptTypeLiteral = Literal["topic", "subtopic", "concept", "skill"]
RelationLiteral = Literal[
    "PREREQUISITE_OF",
    "PART_OF",
    "DERIVED_FROM",
    "APPLICATION_OF",
    "SPECIAL_CASE_OF",
    "CONTRASTS_WITH",
    "CONFUSED_WITH",
]


# --- LLM extraction output contract (blueprint section 11.4) ---


class ExtractedEdge(BaseModel):
    target_concept_name: str = Field(description="Exact name of another concept extracted in this batch.")
    relation: RelationLiteral


class ExtractedConcept(BaseModel):
    name: str
    definition: str
    concept_type: ConceptTypeLiteral = "concept"
    aliases: list[str] = Field(default_factory=list)
    evidence_indices: list[int] = Field(
        description="Indices into the numbered evidence list that justify this concept."
    )
    edges: list[ExtractedEdge] = Field(default_factory=list)


class ConceptExtractionResult(BaseModel):
    concepts: list[ExtractedConcept]


# --- API contract ---


class ConceptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    canonical_name: str
    slug: str
    definition: str | None
    concept_type: str
    status: str
    created_at: datetime


class ConceptListResponse(BaseModel):
    items: list[ConceptRead]
    total: int


class ConceptEdgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_concept_id: uuid.UUID
    target_concept_id: uuid.UUID
    relation: str
    confidence: float
    provenance_type: str
    approved: bool


class ConceptDetailRead(ConceptRead):
    outgoing_edges: list[ConceptEdgeRead]
    incoming_edges: list[ConceptEdgeRead]
    evidence_chunk_ids: list[uuid.UUID]


class ConceptUpdate(BaseModel):
    canonical_name: str | None = Field(default=None, max_length=255)
    definition: str | None = None
    concept_type: ConceptTypeLiteral | None = None
    status: Literal["PROPOSED", "APPROVED", "REJECTED"] | None = None


class MergeConceptsRequest(BaseModel):
    absorb_concept_id: uuid.UUID = Field(description="Concept to merge INTO this one; it will be deleted.")


class BuildCurriculumResponse(BaseModel):
    concepts_created: int
    concepts_updated: int
    edges_created: int
    edges_skipped_cycle: int
    chunks_considered: int
