"""SQL helpers for operations layer."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from psycopg import Cursor

STALE_SWEEP_AUDIT_SQL = """
UPDATE audit_runs
SET status = 'stale',
    finished_at = now(),
    error = 'sweeper_timeout'
WHERE status = 'processing'
  AND started_at < (now() - (%s::int * interval '1 minute'))
"""

FETCH_AUDIT_USAGE_FOR_DATE_SQL = """
SELECT id, report_json
FROM audit_runs
WHERE task_date = %s
  AND status IN ('completed', 'completed_cached')
ORDER BY started_at
"""

UPSERT_AUDIT_COST_DAILY_SQL = """
INSERT INTO audit_cost_daily (rollup_date, runs_count, input_tokens, output_tokens, cost_usd, rollup_at)
VALUES (%s, %s, %s, %s, %s, now())
ON CONFLICT (rollup_date)
DO UPDATE SET
    runs_count = EXCLUDED.runs_count,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    cost_usd = EXCLUDED.cost_usd,
    rollup_at = now()
"""

FETCH_RECENT_COST_HISTORY_SQL = """
SELECT rollup_date, cost_usd::float
FROM audit_cost_daily
WHERE rollup_date < %s
ORDER BY rollup_date DESC
LIMIT %s
"""

FETCH_DB_HEALTH_SQL = "SELECT 1"

FETCH_TABLE_COUNT_SQL_TEMPLATE = "SELECT count(*) FROM {table_name}"

FETCH_MAX_TS_SQL_TEMPLATE = "SELECT MAX({column_name}) FROM {table_name}"

FETCH_RECENT_AUDIT_FAILURE_RATE_SQL = """
SELECT
  COUNT(*) FILTER (WHERE status = 'failed')::int AS failed_runs,
  COUNT(*)::int AS total_runs
FROM audit_runs
WHERE task_date >= (%s::date - interval '7 days')
  AND task_date <= %s::date
"""


def sweep_stale_audit_runs(cur: Cursor[object], threshold_minutes: int) -> int:
    """Mark stale audit runs and return number of updated rows."""

    cur.execute(STALE_SWEEP_AUDIT_SQL, (threshold_minutes,))
    return cur.rowcount


def fetch_audit_usage_for_date(cur: Cursor[object], rollup_date: date) -> list[tuple[Any, ...]]:
    """Return audit runs with report_json for one task date."""

    cur.execute(FETCH_AUDIT_USAGE_FOR_DATE_SQL, (rollup_date,))
    return cast(list[tuple[Any, ...]], cur.fetchall())


def upsert_audit_cost_daily(
    cur: Cursor[object],
    *,
    rollup_date: date,
    runs_count: int,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> None:
    """Upsert one daily audit cost rollup row."""

    cur.execute(
        UPSERT_AUDIT_COST_DAILY_SQL,
        (
            rollup_date,
            runs_count,
            input_tokens,
            output_tokens,
            cost_usd,
        ),
    )


def fetch_recent_cost_history(cur: Cursor[object], rollup_date: date, limit: int = 7) -> list[float]:
    """Return historical cost values before rollup date."""

    cur.execute(FETCH_RECENT_COST_HISTORY_SQL, (rollup_date, limit))
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return [float(row[1]) for row in rows]


def fetch_db_health(cur: Cursor[object]) -> bool:
    """Return True when SELECT 1 is successful."""

    cur.execute(FETCH_DB_HEALTH_SQL)
    row = cast(tuple[Any, ...] | None, cur.fetchone())
    return row is not None and int(row[0]) == 1


def fetch_table_count(cur: Cursor[object], table_name: str) -> int:
    """Read exact count from a known table name."""

    allowed = {"raw_tasks", "tasks_normalized", "audit_runs", "pipeline_errors"}
    if table_name not in allowed:
        raise ValueError(f"Unsupported table name: {table_name}")

    sql = FETCH_TABLE_COUNT_SQL_TEMPLATE.format(table_name=table_name)
    cur.execute(sql)
    row = cast(tuple[Any, ...] | None, cur.fetchone())
    if row is None:
        return 0
    return int(row[0])


def fetch_table_max_timestamp(cur: Cursor[object], table_name: str, column_name: str) -> Any | None:
    """Read max timestamp/date from known table and column names."""

    allowed = {
        ("raw_tasks", "parsed_at"),
        ("tasks_normalized", "normalized_at"),
        ("audit_runs", "started_at"),
    }
    if (table_name, column_name) not in allowed:
        raise ValueError(f"Unsupported table+column: {table_name}.{column_name}")

    sql = FETCH_MAX_TS_SQL_TEMPLATE.format(table_name=table_name, column_name=column_name)
    cur.execute(sql)
    row = cast(tuple[Any, ...] | None, cur.fetchone())
    if row is None:
        return None
    return row[0]


def fetch_recent_audit_failure_rate(cur: Cursor[object], target_date: date) -> tuple[int, int]:
    """Return failed/total run counts for recent audit window."""

    cur.execute(FETCH_RECENT_AUDIT_FAILURE_RATE_SQL, (target_date, target_date))
    row = cast(tuple[Any, ...] | None, cur.fetchone())
    if row is None:
        return (0, 0)
    return (int(row[0]), int(row[1]))
