"""Create knowledge_base_articles table for methodology indexing."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_knowledge_base_articles"
down_revision = "0011_dynamic_task_norms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_base_articles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::TEXT[]"),
        ),
        sa.Column(
            "fts",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(body,''))",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("source_path", name="uq_knowledge_base_articles_source_path"),
    )

    op.create_index(
        "ix_knowledge_base_articles_fts",
        "knowledge_base_articles",
        ["fts"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_base_articles_fts", table_name="knowledge_base_articles")
    op.drop_table("knowledge_base_articles")
