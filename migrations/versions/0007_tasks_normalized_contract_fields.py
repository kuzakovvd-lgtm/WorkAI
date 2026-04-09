"""Align tasks_normalized with spec contract fields for normalize->assess."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_tasks_norm_contract"
down_revision = "0006_employee_daily_ghost_time"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("employee_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_name_norm", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("employee_name_norm", name="uq_employees_employee_name_norm"),
    )

    op.add_column("tasks_normalized", sa.Column("raw_task_id", sa.BigInteger(), nullable=True))
    op.add_column("tasks_normalized", sa.Column("task_date", sa.Date(), nullable=True))
    op.add_column("tasks_normalized", sa.Column("employee_id", sa.Integer(), nullable=True))
    op.add_column("tasks_normalized", sa.Column("canonical_text", sa.Text(), nullable=True))
    op.add_column("tasks_normalized", sa.Column("task_category", sa.Text(), nullable=True))
    op.add_column(
        "tasks_normalized",
        sa.Column("time_source", sa.Text(), nullable=False, server_default=sa.text("'none'")),
    )
    op.add_column(
        "tasks_normalized",
        sa.Column("is_smart", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "tasks_normalized",
        sa.Column("is_micro", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "tasks_normalized",
        sa.Column("result_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "tasks_normalized",
        sa.Column("is_zhdun", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.execute(
        """
        INSERT INTO employees (employee_name_norm)
        SELECT DISTINCT employee_name_norm
        FROM tasks_normalized
        WHERE employee_name_norm IS NOT NULL
        ON CONFLICT (employee_name_norm) DO NOTHING
        """
    )

    op.execute(
        """
        UPDATE tasks_normalized AS tn
        SET
            task_date = tn.work_date,
            canonical_text = tn.task_text_norm,
            task_category = tn.category_code,
            time_source = CASE WHEN tn.duration_minutes IS NULL THEN 'none' ELSE 'parsed' END,
            result_confirmed = CASE WHEN tn.duration_minutes IS NULL THEN false ELSE true END,
            is_micro = CASE WHEN tn.duration_minutes IS NOT NULL AND tn.duration_minutes <= 15 THEN true ELSE false END,
            is_smart = false,
            is_zhdun = false
        """
    )

    op.execute(
        """
        UPDATE tasks_normalized AS tn
        SET employee_id = e.employee_id
        FROM employees AS e
        WHERE e.employee_name_norm = tn.employee_name_norm
        """
    )

    op.execute(
        """
        UPDATE tasks_normalized AS tn
        SET raw_task_id = rt.raw_task_id
        FROM raw_tasks AS rt
        WHERE rt.spreadsheet_id = tn.spreadsheet_id
          AND rt.sheet_title = tn.sheet_title
          AND rt.row_idx = tn.row_idx
          AND rt.col_idx = tn.col_idx
          AND rt.line_no = tn.line_no
        """
    )

    op.create_index("ix_tasks_normalized_employee_id_task_date", "tasks_normalized", ["employee_id", "task_date"])

    op.alter_column("tasks_normalized", "task_date", nullable=False)
    op.alter_column("tasks_normalized", "employee_id", nullable=False)
    op.alter_column("tasks_normalized", "canonical_text", nullable=False)

    op.create_foreign_key(
        "fk_tasks_normalized_employee_id",
        "tasks_normalized",
        "employees",
        ["employee_id"],
        ["employee_id"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "fk_tasks_normalized_raw_task_id",
        "tasks_normalized",
        "raw_tasks",
        ["raw_task_id"],
        ["raw_task_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_tasks_normalized_raw_task_id", "tasks_normalized", type_="foreignkey")
    op.drop_constraint("fk_tasks_normalized_employee_id", "tasks_normalized", type_="foreignkey")
    op.drop_index("ix_tasks_normalized_employee_id_task_date", table_name="tasks_normalized")

    op.drop_column("tasks_normalized", "is_zhdun")
    op.drop_column("tasks_normalized", "result_confirmed")
    op.drop_column("tasks_normalized", "is_micro")
    op.drop_column("tasks_normalized", "is_smart")
    op.drop_column("tasks_normalized", "time_source")
    op.drop_column("tasks_normalized", "task_category")
    op.drop_column("tasks_normalized", "canonical_text")
    op.drop_column("tasks_normalized", "employee_id")
    op.drop_column("tasks_normalized", "task_date")
    op.drop_column("tasks_normalized", "raw_task_id")

    op.drop_table("employees")
