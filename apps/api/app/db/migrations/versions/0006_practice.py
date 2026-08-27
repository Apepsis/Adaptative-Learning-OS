"""practice: questions, practice_sessions, attempts, attempt_errors

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-26

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("question_type", sa.String(length=16), nullable=False),
        sa.Column("stem", sa.String(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column("correct_option_id", sa.String(length=8), nullable=True),
        sa.Column("numeric_answer", sa.Numeric(12, 4), nullable=True),
        sa.Column("numeric_tolerance", sa.Numeric(12, 4), nullable=True),
        sa.Column("units", sa.String(length=32), nullable=True),
        sa.Column("sample_answer", sa.String(), nullable=True),
        sa.Column("hints", postgresql.JSONB(), nullable=True),
        sa.Column("solution_text", sa.String(), nullable=True),
        sa.Column("difficulty_level", sa.String(length=4), nullable=True),
        sa.Column("verification_state", sa.String(length=16), nullable=False, server_default="unverified"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], name="fk_questions_subject_id_subjects", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["concepts.id"], name="fk_questions_concept_id_concepts", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_questions_subject_id", "questions", ["subject_id"])
    op.create_index("ix_questions_concept_id", "questions", ["concept_id"])

    op.create_table(
        "practice_sessions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_ids", postgresql.JSONB(), nullable=False),
        sa.Column("current_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_practice_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], name="fk_practice_sessions_subject_id_subjects", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_practice_sessions_user_id", "practice_sessions", ["user_id"])
    op.create_index("ix_practice_sessions_subject_id", "practice_sessions", ["subject_id"])

    op.create_table(
        "attempts",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_answer", postgresql.JSONB(), nullable=False),
        sa.Column("elapsed_ms", sa.Integer(), nullable=True),
        sa.Column("score", sa.Numeric(4, 3), nullable=False),
        sa.Column("max_score", sa.Numeric(4, 3), nullable=False, server_default="1.0"),
        sa.Column("correctness", sa.String(length=16), nullable=False),
        sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("solution_revealed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("feedback", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_attempts_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"], name="fk_attempts_question_id_questions", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["practice_sessions.id"], name="fk_attempts_session_id_practice_sessions", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_attempts_user_id", "attempts", ["user_id"])
    op.create_index("ix_attempts_question_id", "attempts", ["question_id"])
    op.create_index("ix_attempts_session_id", "attempts", ["session_id"])

    op.create_table(
        "attempt_errors",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("error_type", sa.String(length=32), nullable=False),
        sa.Column("explanation", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["attempts.id"], name="fk_attempt_errors_attempt_id_attempts", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_attempt_errors_attempt_id", "attempt_errors", ["attempt_id"])


def downgrade() -> None:
    op.drop_table("attempt_errors")
    op.drop_table("attempts")
    op.drop_table("practice_sessions")
    op.drop_table("questions")
