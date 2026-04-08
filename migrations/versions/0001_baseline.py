"""Baseline revision for WorkAI Phase 1."""

from __future__ import annotations

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply baseline schema revision.

    Phase 1 stores an empty baseline because business schema is introduced in later phases.
    """

    pass


def downgrade() -> None:
    """Revert baseline revision."""

    pass
