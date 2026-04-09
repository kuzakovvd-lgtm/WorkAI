"""Create audit_runs, audit_feedback and audit_cost_daily contract tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_audit_tables"
down_revision = "0012_knowledge_base_articles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "audit_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("task_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("forced", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint(
            "status IN ('processing','completed','completed_cached','failed','stale')",
            name="ck_audit_runs_status",
        ),
    )
    op.create_index(
        "ix_audit_runs_employee_task_started_desc",
        "audit_runs",
        ["employee_id", "task_date", "started_at"],
    )
    op.create_index(
        "ix_audit_runs_processing",
        "audit_runs",
        ["employee_id", "task_date", "started_at"],
        postgresql_where=sa.text("status = 'processing'"),
    )

    op.create_table(
        "audit_feedback",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["audit_runs.id"], ondelete="CASCADE", name="fk_audit_feedback_run_id"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_audit_feedback_rating_range"),
    )

    op.create_table(
        "audit_cost_daily",
        sa.Column("rollup_date", sa.Date(), primary_key=True, nullable=False),
        sa.Column("runs_count", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), nullable=False),
        sa.Column("output_tokens", sa.BigInteger(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("rollup_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("audit_cost_daily")
    op.drop_table("audit_feedback")
    op.drop_index("ix_audit_runs_processing", table_name="audit_runs")
    op.drop_index("ix_audit_runs_employee_task_started_desc", table_name="audit_runs")
    op.drop_table("audit_runs")
