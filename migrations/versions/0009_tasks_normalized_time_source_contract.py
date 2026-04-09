"""Constrain tasks_normalized.time_source to contract values only."""

from __future__ import annotations

from alembic import op

revision = "0009_tasks_norm_time_source"
down_revision = "0008_daily_task_assess"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute(
        """
        UPDATE tasks_normalized
        SET time_source = 'logged'
        WHERE time_source = 'parsed'
        """
    )
    op.execute(
        """
        UPDATE tasks_normalized
        SET time_source = 'none'
        WHERE time_source IS NULL
           OR time_source NOT IN ('logged', 'estimated', 'inferred', 'none')
        """
    )
    op.create_check_constraint(
        "ck_tasks_normalized_time_source_allowed",
        "tasks_normalized",
        "time_source IN ('logged', 'estimated', 'inferred', 'none')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_tasks_normalized_time_source_allowed",
        "tasks_normalized",
        type_="check",
    )
