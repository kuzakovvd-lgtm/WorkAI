"""Create operational_cycles contract table for assess aggregation step."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_operational_cycles"
down_revision = "0009_tasks_norm_time_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_cycles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("task_date", sa.Date(), nullable=False),
        sa.Column("cycle_key", sa.Text(), nullable=False),
        sa.Column("canonical_text", sa.Text(), nullable=False),
        sa.Column("task_category", sa.Text(), nullable=False),
        sa.Column("total_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("tasks_count", sa.Integer(), nullable=False),
        sa.Column("is_zhdun", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("avg_quality_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("avg_smart_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.employee_id"], name="fk_operational_cycles_employee_id", ondelete="RESTRICT"),
        sa.UniqueConstraint("employee_id", "task_date", "cycle_key", name="uq_operational_cycles_employee_date_key"),
    )
    op.create_index(
        "ix_operational_cycles_employee_task_date",
        "operational_cycles",
        ["employee_id", "task_date"],
    )
    op.create_index(
        "ix_operational_cycles_task_date",
        "operational_cycles",
        ["task_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_operational_cycles_task_date", table_name="operational_cycles")
    op.drop_index("ix_operational_cycles_employee_task_date", table_name="operational_cycles")
    op.drop_table("operational_cycles")
