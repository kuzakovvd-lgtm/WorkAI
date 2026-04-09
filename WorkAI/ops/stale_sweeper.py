"""Stale run sweeper for operational tables."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from WorkAI.common import configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.ops.models import StaleSweepResult
from WorkAI.ops.queries import sweep_stale_audit_runs

_LOG = get_logger(__name__)


def run_stale_sweeper(
    settings: Settings | None = None,
    *,
    threshold_minutes: int = 15,
) -> StaleSweepResult:
    """Mark stale runs in DB and return summary."""

    resolved = settings or get_settings()
    configure_logging(resolved)
    init_db(resolved)

    per_table: dict[str, int] = {}

    try:
        with connection() as conn, conn.cursor() as cur:
            audit_updated = sweep_stale_audit_runs(cur, threshold_minutes)
            per_table["audit_runs"] = audit_updated
            conn.commit()
    finally:
        close_db()

    result = StaleSweepResult(
        tables_checked=["audit_runs"],
        rows_updated=sum(per_table.values()),
        per_table=per_table,
        threshold_minutes=threshold_minutes,
        finished_at=datetime.now(UTC),
    )

    _LOG.info(
        "stale_sweeper_completed",
        tables_checked=result.tables_checked,
        rows_updated=result.rows_updated,
        threshold_minutes=threshold_minutes,
    )
    return result


def stale_sweeper_to_dict(result: StaleSweepResult) -> dict[str, object]:
    """Serialize stale sweeper summary for CLI output."""

    payload = asdict(result)
    payload["finished_at"] = result.finished_at.isoformat()
    return payload
