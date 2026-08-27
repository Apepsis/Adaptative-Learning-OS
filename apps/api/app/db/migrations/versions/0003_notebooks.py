"""notebooks: notebooks, notebook_sources, notebook_notes, notebook_messages

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-26

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notebooks",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notebooks_user_id_users", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_notebooks_user_id", "notebooks", ["user_id"])

    op.create_table(
        "notebook_sources",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["notebook_id"], ["notebooks.id"], name="fk_notebook_sources_notebook_id_notebooks", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name="fk_notebook_sources_source_id_sources", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("notebook_id", "source_id", name="uq_notebook_sources_pair"),
    )
    op.create_index("ix_notebook_sources_notebook_id", "notebook_sources", ["notebook_id"])
    op.create_index("ix_notebook_sources_source_id", "notebook_sources", ["source_id"])

    op.create_table(
        "notebook_notes",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="Untitled note"),
        sa.Column("content", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["notebook_id"], ["notebooks.id"], name="fk_notebook_notes_notebook_id_notebooks", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_notebook_notes_notebook_id", "notebook_notes", ["notebook_id"])

    op.create_table(
        "notebook_messages",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("not_found", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["notebook_id"], ["notebooks.id"], name="fk_notebook_messages_notebook_id_notebooks", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_notebook_messages_notebook_id", "notebook_messages", ["notebook_id"])


def downgrade() -> None:
    op.drop_table("notebook_messages")
    op.drop_table("notebook_notes")
    op.drop_table("notebook_sources")
    op.drop_table("notebooks")
