"""learn: flashcards, study_guides

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-26

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "flashcards",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("front", sa.String(), nullable=False),
        sa.Column("back", sa.String(), nullable=False),
        sa.Column("source_grounded", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], name="fk_flashcards_subject_id_subjects", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["concepts.id"], name="fk_flashcards_concept_id_concepts", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_flashcards_subject_id", "flashcards", ["subject_id"])
    op.create_index("ix_flashcards_concept_id", "flashcards", ["concept_id"])

    op.create_table(
        "study_guides",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], name="fk_study_guides_subject_id_subjects", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("subject_id", name="uq_study_guides_subject_id"),
    )


def downgrade() -> None:
    op.drop_table("study_guides")
    op.drop_table("flashcards")
