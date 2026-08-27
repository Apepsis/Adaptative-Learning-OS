import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MisconceptionStatus(enum.StrEnum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"


class ConceptMastery(Base):
    """Blueprint 7.9 / 16.1. One row per (user, concept), updated after
    every graded attempt on a question tagged with that concept."""

    __tablename__ = "concept_mastery"
    __table_args__ = (UniqueConstraint("user_id", "concept_id", name="uq_concept_mastery_user_concept"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    p_mastery: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False), nullable=False, server_default="0.2")
    mastery_confidence: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False), nullable=False, server_default="0")
    recent_accuracy: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False), nullable=False, server_default="0")
    weighted_accuracy: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False), nullable=False, server_default="0")
    # No mechanism yet marks an attempt as a "transfer" context (blueprint
    # 16.7 needs that tag on the attempt itself) — always 0.0 until that
    # lands. See docs/adr/0006-learner-model-simplifications.md.
    transfer_score: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False), nullable=False, server_default="0")
    hint_independence: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False), nullable=False, server_default="1")
    speed_index: Mapped[float | None] = mapped_column(Numeric(6, 3, asdecimal=False), nullable=True)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    distinct_question_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_evidence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MasteryEvent(Base):
    """Append-only log (blueprint 7.9: "evento append-only para poder
    recalcular el modelo") — the BKT before/after for one attempt."""

    __tablename__ = "mastery_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    p_before: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False), nullable=False)
    p_after: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(4, 3, asdecimal=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Misconception(Base):
    """Blueprint 15.2 + 15.4, simplified to be per-user rather than a
    shared catalog (this is a personal LOS, single-user per blueprint
    section 27) — see docs/adr/0006-learner-model-simplifications.md."""

    __tablename__ = "misconceptions"
    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", "error_type", name="uq_misconceptions_user_concept_error"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    error_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=MisconceptionStatus.CANDIDATE.value
    )
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    distinct_question_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReviewState(Base):
    """FSRS scheduling state for one flashcard (blueprint 7.10), backed by
    the real `fsrs` library — see fsrs_adapter.py. `state` mirrors
    fsrs.State's own int values (1=Learning, 2=Review, 3=Relearning)."""

    __tablename__ = "review_state"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    flashcard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    state: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stability: Mapped[float | None] = mapped_column(Numeric(10, 4, asdecimal=False), nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Numeric(10, 4, asdecimal=False), nullable=True)
    due: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FlashcardReview(Base):
    """Review log (blueprint 17.3)."""

    __tablename__ = "flashcard_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    review_state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("review_state.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[str] = mapped_column(String(8), nullable=False)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
