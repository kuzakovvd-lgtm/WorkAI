"""Create employee_daily_ghost_time table for assess ghost time step."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_employee_daily_ghost_time"
down_revision = "0005_pipeline_errors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_daily_ghost_time",
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("task_date", sa.Date(), nullable=False),
        sa.Column("workday_minutes", sa.Integer(), nullable=False, server_default=sa.text("480")),
        sa.Column("logged_minutes", sa.Integer(), nullable=False),
        sa.Column("ghost_minutes", sa.Integer(), nullable=False),
        sa.Column("index_of_trust_base", sa.Numeric(4, 3), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("employee_id", "task_date", name="pk_employee_daily_ghost_time"),
    )
    op.create_index(
        "ix_employee_daily_ghost_time_task_date",
        "employee_daily_ghost_time",
        ["task_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_employee_daily_ghost_time_task_date", table_name="employee_daily_ghost_time")
    op.drop_table("employee_daily_ghost_time")
