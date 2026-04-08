"""Create sheet_cells table for ingest layer."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# TODO(TZ §3.2): align final column set and indexes with full product schema section.
revision = "0002_sheet_cells"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sheet_cells",
        sa.Column("spreadsheet_id", sa.Text(), nullable=False),
        sa.Column("sheet_title", sa.Text(), nullable=False),
        sa.Column("row_idx", sa.Integer(), nullable=False),
        sa.Column("col_idx", sa.Integer(), nullable=False),
        sa.Column("a1", sa.Text(), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("spreadsheet_id", "sheet_title", "row_idx", "col_idx", name="pk_sheet_cells"),
    )
    op.create_index(
        "ix_sheet_cells_spreadsheet_sheet",
        "sheet_cells",
        ["spreadsheet_id", "sheet_title"],
    )


def downgrade() -> None:
    op.drop_index("ix_sheet_cells_spreadsheet_sheet", table_name="sheet_cells")
    op.drop_table("sheet_cells")
