"""Create pipeline_errors table for DLQ-style record-level failures."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_pipeline_errors"
down_revision = "0004_tasks_normalized"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_errors",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("phase", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("sheet_id", sa.Text(), nullable=True),
        sa.Column("work_date", sa.Date(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("error_type", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("payload_excerpt", sa.Text(), nullable=True),
        sa.Column("error_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_pipeline_errors_phase_created_at",
        "pipeline_errors",
        ["phase", "created_at"],
    )
    op.create_index(
        "ix_pipeline_errors_sheet_work_date",
        "pipeline_errors",
        ["sheet_id", "work_date"],
    )
    op.create_index(
        "ix_pipeline_errors_run_id",
        "pipeline_errors",
        ["run_id"],
    )
    op.create_unique_constraint(
        "uq_pipeline_errors_phase_source_hash",
        "pipeline_errors",
        ["phase", "source_ref", "error_hash"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_pipeline_errors_phase_source_hash", "pipeline_errors", type_="unique")
    op.drop_index("ix_pipeline_errors_run_id", table_name="pipeline_errors")
    op.drop_index("ix_pipeline_errors_sheet_work_date", table_name="pipeline_errors")
    op.drop_index("ix_pipeline_errors_phase_created_at", table_name="pipeline_errors")
    op.drop_table("pipeline_errors")
