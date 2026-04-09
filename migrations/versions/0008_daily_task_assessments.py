"""Add tasks_normalized id and daily_task_assessments for assess scoring step."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_daily_task_assess"
down_revision = "0007_tasks_norm_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tasks_normalized ADD COLUMN id BIGSERIAL")
    op.create_primary_key("pk_tasks_normalized_id", "tasks_normalized", ["id"])

    op.create_table(
        "daily_task_assessments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("normalized_task_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("task_date", sa.Date(), nullable=False),
        sa.Column("norm_minutes", sa.Integer(), nullable=True),
        sa.Column("delta_minutes", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("smart_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["normalized_task_id"],
            ["tasks_normalized.id"],
            name="fk_daily_task_assessments_normalized_task_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("normalized_task_id", name="uq_daily_task_assessments_normalized_task_id"),
    )
    op.create_index(
        "ix_daily_task_assessments_employee_task_date",
        "daily_task_assessments",
        ["employee_id", "task_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_daily_task_assessments_employee_task_date",
        table_name="daily_task_assessments",
    )
    op.drop_table("daily_task_assessments")

    op.drop_constraint("pk_tasks_normalized_id", "tasks_normalized", type_="primary")
    op.drop_column("tasks_normalized", "id")
