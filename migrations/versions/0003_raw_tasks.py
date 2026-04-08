"""Create raw_tasks table for parse layer."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# TODO(TZ §3.3): align with full schema section when external TZ is available.
revision = "0003_raw_tasks"
down_revision = "0002_sheet_cells"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_tasks",
        sa.Column("raw_task_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("spreadsheet_id", sa.Text(), nullable=False),
        sa.Column("sheet_title", sa.Text(), nullable=False),
        sa.Column("row_idx", sa.Integer(), nullable=False),
        sa.Column("col_idx", sa.Integer(), nullable=False),
        sa.Column("cell_a1", sa.Text(), nullable=False),
        sa.Column("cell_ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("employee_name_raw", sa.Text(), nullable=True),
        sa.Column("work_date", sa.Date(), nullable=True),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("line_text", sa.Text(), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint(
        "uq_raw_tasks_cell_line",
        "raw_tasks",
        ["spreadsheet_id", "sheet_title", "row_idx", "col_idx", "line_no"],
    )
    op.create_index(
        "ix_raw_tasks_spreadsheet_sheet",
        "raw_tasks",
        ["spreadsheet_id", "sheet_title"],
    )
    op.create_index(
        "ix_raw_tasks_employee_date",
        "raw_tasks",
        ["employee_name_raw", "work_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_raw_tasks_employee_date", table_name="raw_tasks")
    op.drop_index("ix_raw_tasks_spreadsheet_sheet", table_name="raw_tasks")
    op.drop_constraint("uq_raw_tasks_cell_line", "raw_tasks", type_="unique")
    op.drop_table("raw_tasks")
