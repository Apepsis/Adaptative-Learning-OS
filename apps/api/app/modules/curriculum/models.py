import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConceptStatus(enum.StrEnum):
    """Blueprint section 11.5."""

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    MERGED = "MERGED"
    REJECTED = "REJECTED"


class ConceptRelation(enum.StrEnum):
    """Blueprint section 11.7 — deliberately kept to relations with actual
    functional use; no relation type is added speculatively."""

    PREREQUISITE_OF = "PREREQUISITE_OF"
    PART_OF = "PART_OF"
    DERIVED_FROM = "DERIVED_FROM"
    APPLICATION_OF = "APPLICATION_OF"
    SPECIAL_CASE_OF = "SPECIAL_CASE_OF"
    CONTRASTS_WITH = "CONTRASTS_WITH"
    CONFUSED_WITH = "CONFUSED_WITH"


class ConceptProvenance(enum.StrEnum):
    SYLLABUS = "syllabus"
    SOURCE = "source"
    MODEL = "model"
    USER = "user"


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("subject_id", "slug", name="uq_concepts_subject_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[str | None] = mapped_column(String, nullable=True)
    # "topic" | "subtopic" | "concept" | "skill" — an emergent hierarchy via
    # PART_OF edges + this hint, not a separate modules table (see
    # docs/adr/0003-concept-graph-doubles-as-topic-tree.md).
    concept_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="concept")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=ConceptStatus.PROPOSED.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConceptAlias(Base):
    __tablename__ = "concept_aliases"
    __table_args__ = (UniqueConstraint("concept_id", "alias", name="uq_concept_aliases_pair"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)


class ConceptEdge(Base):
    __tablename__ = "concept_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_concept_id", "target_concept_id", "relation", name="uq_concept_edges_triple"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3, asdecimal=False), nullable=False, server_default="1.0")
    provenance_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConceptEvidence(Base):
    """Links a concept to the chunk(s) that justify it (blueprint 7.6)."""

    __tablename__ = "concept_evidence"
    __table_args__ = (UniqueConstraint("concept_id", "chunk_id", name="uq_concept_evidence_pair"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
