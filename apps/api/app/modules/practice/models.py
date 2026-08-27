import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuestionType(enum.StrEnum):
    MCQ = "mcq"
    NUMERIC = "numeric"
    SHORT_ANSWER = "short_answer"


class QuestionOrigin(enum.StrEnum):
    """Subset of blueprint section 13.1 — OFFICIAL/TEXTBOOK/TEACHER import
    pipelines (section 13.2) aren't built yet, so only the two origins
    this phase actually produces exist."""

    USER = "user"
    GENERATED = "generated"


class VerificationState(enum.StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    QUARANTINED = "quarantined"


class Correctness(enum.StrEnum):
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"


class Question(Base):
    """Blueprint section 7.8, simplified: type-specific columns instead of
    a generic answer_schema/markscheme JSONB, since this phase only
    supports three fixed types. See docs/adr/0005-simplified-question-schema.md."""

    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    question_type: Mapped[str] = mapped_column(String(16), nullable=False)
    stem: Mapped[str] = mapped_column(String, nullable=False)

    # MCQ
    options: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{"id": "a", "text": "..."}]
    correct_option_id: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # Numeric
    numeric_answer: Mapped[float | None] = mapped_column(Numeric(12, 4, asdecimal=False), nullable=True)
    numeric_tolerance: Mapped[float | None] = mapped_column(Numeric(12, 4, asdecimal=False), nullable=True)
    units: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Short answer
    sample_answer: Mapped[str | None] = mapped_column(String, nullable=True)

    hints: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # list[str], ladder order
    solution_text: Mapped[str | None] = mapped_column(String, nullable=True)
    difficulty_level: Mapped[str | None] = mapped_column(String(4), nullable=True)  # "L0".."L5"
    verification_state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=VerificationState.UNVERIFIED.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_ids: Mapped[list] = mapped_column(JSONB, nullable=False)  # ordered list of str(uuid)
    current_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("practice_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    raw_answer: Mapped[dict] = mapped_column(JSONB, nullable=False)
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float] = mapped_column(Numeric(4, 3, asdecimal=False), nullable=False)
    max_score: Mapped[float] = mapped_column(Numeric(4, 3, asdecimal=False), nullable=False, server_default="1.0")
    correctness: Mapped[str] = mapped_column(String(16), nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    solution_revealed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    feedback: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AttemptError(Base):
    """Basic error classification (blueprint section 15). `concept_id` and
    `misconception_id` (blueprint 7.8) were added in Phase 7 once
    app.modules.mastery existed to populate them — see
    app.modules.mastery.service.record_attempt_outcome."""

    __tablename__ = "attempt_errors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    error_type: Mapped[str] = mapped_column(String(32), nullable=False)
    misconception_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("misconceptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
