"""Create dynamic_task_norms table for assess Bayesian norms step."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_dynamic_task_norms"
down_revision = "0010_operational_cycles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dynamic_task_norms",
        sa.Column("task_category", sa.Text(), primary_key=True, nullable=False),
        sa.Column("norm_minutes", sa.Numeric(7, 2), nullable=False),
        sa.Column("stddev_minutes", sa.Numeric(7, 2), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("baseline_prior", sa.Numeric(7, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("dynamic_task_norms")
