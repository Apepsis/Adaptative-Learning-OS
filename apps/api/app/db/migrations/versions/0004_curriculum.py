"""curriculum: concepts, concept_aliases, concept_edges, concept_evidence

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-26

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "concepts",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("definition", sa.String(), nullable=True),
        sa.Column("concept_type", sa.String(length=32), nullable=False, server_default="concept"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PROPOSED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], name="fk_concepts_subject_id_subjects", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("subject_id", "slug", name="uq_concepts_subject_slug"),
    )
    op.create_index("ix_concepts_subject_id", "concepts", ["subject_id"])

    op.create_table(
        "concept_aliases",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["concepts.id"], name="fk_concept_aliases_concept_id_concepts", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("concept_id", "alias", name="uq_concept_aliases_pair"),
    )
    op.create_index("ix_concept_aliases_concept_id", "concept_aliases", ["concept_id"])

    op.create_table(
        "concept_edges",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="1.0"),
        sa.Column("provenance_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], name="fk_concept_edges_subject_id_subjects", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_concept_id"], ["concepts.id"], name="fk_concept_edges_source_concept_id_concepts", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_concept_id"], ["concepts.id"], name="fk_concept_edges_target_concept_id_concepts", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name="fk_concept_edges_source_id_sources", ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "source_concept_id", "target_concept_id", "relation", name="uq_concept_edges_triple"
        ),
    )
    op.create_index("ix_concept_edges_subject_id", "concept_edges", ["subject_id"])
    op.create_index("ix_concept_edges_source_concept_id", "concept_edges", ["source_concept_id"])
    op.create_index("ix_concept_edges_target_concept_id", "concept_edges", ["target_concept_id"])

    op.create_table(
        "concept_evidence",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["concepts.id"], name="fk_concept_evidence_concept_id_concepts", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["chunks.id"], name="fk_concept_evidence_chunk_id_chunks", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("concept_id", "chunk_id", name="uq_concept_evidence_pair"),
    )
    op.create_index("ix_concept_evidence_concept_id", "concept_evidence", ["concept_id"])
    op.create_index("ix_concept_evidence_chunk_id", "concept_evidence", ["chunk_id"])


def downgrade() -> None:
    op.drop_table("concept_evidence")
    op.drop_table("concept_edges")
    op.drop_table("concept_aliases")
    op.drop_table("concepts")
