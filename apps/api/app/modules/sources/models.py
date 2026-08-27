import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SourceType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    IMAGE = "image"


class SourceStatus(str, enum.Enum):
    """Subset of the full ingestion state machine (blueprint section 8.1)
    that Phase 1 actually drives. Parsing/normalizing/chunking/indexing
    states are introduced in Phase 2 once a real pipeline exists."""

    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    FAILED = "FAILED"


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        Index("ix_sources_user_sha256", "user_id", "sha256"),
        Index("ix_sources_subject_id", "subject_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True
    )

    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)

    source_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trust_tier: Mapped[float | None] = mapped_column(Numeric(4, 3, asdecimal=False), nullable=True)

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=SourceStatus.UPLOADED.value
    )
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
