"""Create tasks_normalized table for normalize layer."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# TODO(TZ §5): align with external schema when full product TZ is available.
revision = "0004_tasks_normalized"
down_revision = "0003_raw_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks_normalized",
        sa.Column("spreadsheet_id", sa.Text(), nullable=False),
        sa.Column("sheet_title", sa.Text(), nullable=False),
        sa.Column("row_idx", sa.Integer(), nullable=False),
        sa.Column("col_idx", sa.Integer(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("employee_name_raw", sa.Text(), nullable=False),
        sa.Column("employee_name_norm", sa.Text(), nullable=False),
        sa.Column("employee_match_method", sa.Text(), nullable=False),
        sa.Column("task_text_raw", sa.Text(), nullable=False),
        sa.Column("task_text_norm", sa.Text(), nullable=False),
        sa.Column("time_start", sa.Time(), nullable=True),
        sa.Column("time_end", sa.Time(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("category_code", sa.Text(), nullable=True),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("source_cell_ingested_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_tasks_normalized_natural",
        "tasks_normalized",
        ["spreadsheet_id", "sheet_title", "row_idx", "col_idx", "line_no"],
    )
    op.create_index(
        "ix_tasks_norm_spreadsheet_sheet",
        "tasks_normalized",
        ["spreadsheet_id", "sheet_title"],
    )
    op.create_index(
        "ix_tasks_norm_employee_date",
        "tasks_normalized",
        ["employee_name_norm", "work_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_norm_employee_date", table_name="tasks_normalized")
    op.drop_index("ix_tasks_norm_spreadsheet_sheet", table_name="tasks_normalized")
    op.drop_constraint("uq_tasks_normalized_natural", "tasks_normalized", type_="unique")
    op.drop_table("tasks_normalized")
