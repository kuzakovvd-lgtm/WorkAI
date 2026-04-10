"""Create chunk table for long knowledge documents."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_knowledge_base_chunks"
down_revision = "0014_notification_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_base_chunks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("chunk_no", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column(
            "fts",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('russian', coalesce(chunk_text,''))", persisted=True),
            nullable=False,
        ),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["source_path"],
            ["knowledge_base_articles.source_path"],
            name="fk_knowledge_base_chunks_source_path",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("source_path", "chunk_no", name="uq_knowledge_base_chunks_source_chunk"),
    )

    op.create_index(
        "ix_knowledge_base_chunks_fts",
        "knowledge_base_chunks",
        ["fts"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_knowledge_base_chunks_source_path",
        "knowledge_base_chunks",
        ["source_path"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_base_chunks_source_path", table_name="knowledge_base_chunks")
    op.drop_index("ix_knowledge_base_chunks_fts", table_name="knowledge_base_chunks")
    op.drop_table("knowledge_base_chunks")

