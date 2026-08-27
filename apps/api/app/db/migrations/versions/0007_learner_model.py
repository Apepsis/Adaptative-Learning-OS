"""learner model: concept_mastery, mastery_events, misconceptions,
review_state, flashcard_reviews; attempt_errors gains concept_id/misconception_id

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-26

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "concept_mastery",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("p_mastery", sa.Numeric(5, 4), nullable=False, server_default="0.2"),
        sa.Column("mastery_confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("recent_accuracy", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("weighted_accuracy", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("transfer_score", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("hint_independence", sa.Numeric(5, 4), nullable=False, server_default="1"),
        sa.Column("speed_index", sa.Numeric(6, 3), nullable=True),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_evidence_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_concept_mastery_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["concepts.id"], name="fk_concept_mastery_concept_id_concepts", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", "concept_id", name="uq_concept_mastery_user_concept"),
    )
    op.create_index("ix_concept_mastery_user_id", "concept_mastery", ["user_id"])
    op.create_index("ix_concept_mastery_concept_id", "concept_mastery", ["concept_id"])

    op.create_table(
        "mastery_events",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("p_before", sa.Numeric(5, 4), nullable=False),
        sa.Column("p_after", sa.Numeric(5, 4), nullable=False),
        sa.Column("score", sa.Numeric(4, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_mastery_events_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["concepts.id"], name="fk_mastery_events_concept_id_concepts", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["attempts.id"], name="fk_mastery_events_attempt_id_attempts", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_mastery_events_user_id", "mastery_events", ["user_id"])
    op.create_index("ix_mastery_events_concept_id", "mastery_events", ["concept_id"])
    op.create_index("ix_mastery_events_attempt_id", "mastery_events", ["attempt_id"])

    op.create_table(
        "misconceptions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("error_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="candidate"),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_misconceptions_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["concepts.id"], name="fk_misconceptions_concept_id_concepts", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", "concept_id", "error_type", name="uq_misconceptions_user_concept_error"),
    )
    op.create_index("ix_misconceptions_user_id", "misconceptions", ["user_id"])
    op.create_index("ix_misconceptions_concept_id", "misconceptions", ["concept_id"])

    op.create_table(
        "review_state",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("flashcard_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("step", sa.Integer(), nullable=True),
        sa.Column("stability", sa.Numeric(10, 4), nullable=True),
        sa.Column("difficulty", sa.Numeric(10, 4), nullable=True),
        sa.Column("due", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_review", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["flashcard_id"], ["flashcards.id"], name="fk_review_state_flashcard_id_flashcards", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("flashcard_id", name="uq_review_state_flashcard_id"),
    )
    op.create_index("ix_review_state_flashcard_id", "review_state", ["flashcard_id"])

    op.create_table(
        "flashcard_reviews",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("review_state_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.String(length=8), nullable=False),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["review_state_id"],
            ["review_state.id"],
            name="fk_flashcard_reviews_review_state_id_review_state",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_flashcard_reviews_review_state_id", "flashcard_reviews", ["review_state_id"])

    op.add_column("attempt_errors", sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("attempt_errors", sa.Column("misconception_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_attempt_errors_concept_id_concepts",
        "attempt_errors",
        "concepts",
        ["concept_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_attempt_errors_misconception_id_misconceptions",
        "attempt_errors",
        "misconceptions",
        ["misconception_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_attempt_errors_concept_id", "attempt_errors", ["concept_id"])
    op.create_index("ix_attempt_errors_misconception_id", "attempt_errors", ["misconception_id"])


def downgrade() -> None:
    op.drop_index("ix_attempt_errors_misconception_id", table_name="attempt_errors")
    op.drop_index("ix_attempt_errors_concept_id", table_name="attempt_errors")
    op.drop_constraint("fk_attempt_errors_misconception_id_misconceptions", "attempt_errors", type_="foreignkey")
    op.drop_constraint("fk_attempt_errors_concept_id_concepts", "attempt_errors", type_="foreignkey")
    op.drop_column("attempt_errors", "misconception_id")
    op.drop_column("attempt_errors", "concept_id")

    op.drop_table("flashcard_reviews")
    op.drop_table("review_state")
    op.drop_table("misconceptions")
    op.drop_table("mastery_events")
    op.drop_table("concept_mastery")
