"""SQL helpers for audit runs and prefetch payload."""

from __future__ import annotations

from datetime import date
from typing import Any, cast
from uuid import UUID

from psycopg import Cursor
from psycopg.types.json import Jsonb

from WorkAI.audit.models import AuditPrefetchPayload, AuditRunRecord

FIND_COMPLETED_RUN_SQL = """
SELECT id, employee_id, task_date, status, started_at, finished_at, report_json, forced
FROM audit_runs
WHERE employee_id = %s
  AND task_date = %s
  AND status = 'completed'
ORDER BY started_at DESC
LIMIT 1
"""

INSERT_AUDIT_RUN_SQL = """
INSERT INTO audit_runs (employee_id, task_date, status, report_json, error, forced)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING id, employee_id, task_date, status, started_at, finished_at, report_json, forced
"""

COMPLETE_AUDIT_RUN_SQL = """
UPDATE audit_runs
SET status = 'completed',
    finished_at = now(),
    report_json = %s,
    error = NULL
WHERE id = %s
"""

FAIL_AUDIT_RUN_SQL = """
UPDATE audit_runs
SET status = 'failed',
    finished_at = now(),
    error = %s
WHERE id = %s
"""

FETCH_CYCLES_SQL = """
SELECT
    cycle_key,
    canonical_text,
    task_category,
    total_duration_minutes,
    tasks_count,
    is_zhdun,
    avg_quality_score,
    avg_smart_score
FROM operational_cycles
WHERE employee_id = %s
  AND task_date = %s
ORDER BY cycle_key
"""

FETCH_AUDIT_METRICS_SQL = """
SELECT
    COALESCE(edgt.index_of_trust_base, 0)::float AS index_of_trust_base,
    COALESCE(edgt.ghost_minutes, 0)::float / 60.0 AS ghost_time_hours,
    COALESCE(AVG(CASE WHEN tn.time_source = 'none' THEN 1.0 ELSE 0.0 END), 0.0)::float AS none_time_source_ratio,
    COALESCE(AVG(CASE WHEN tn.is_smart = false THEN 1.0 ELSE 0.0 END), 0.0)::float AS non_smart_ratio
FROM (SELECT %s::int AS employee_id, %s::date AS task_date) AS req
LEFT JOIN employee_daily_ghost_time AS edgt
  ON edgt.employee_id = req.employee_id
 AND edgt.task_date = req.task_date
LEFT JOIN tasks_normalized AS tn
  ON tn.employee_id = req.employee_id
 AND tn.task_date = req.task_date
GROUP BY edgt.index_of_trust_base, edgt.ghost_minutes
"""

FETCH_AUDIT_RUN_SQL = """
SELECT id, employee_id, task_date, status, started_at, finished_at, report_json, forced
FROM audit_runs
WHERE id = %s
"""

INSERT_AUDIT_FEEDBACK_SQL = """
INSERT INTO audit_feedback (run_id, rating, comment, submitted_by)
VALUES (%s, %s, %s, %s)
"""


def find_completed_run(cur: Cursor[object], employee_id: int, task_date: date) -> AuditRunRecord | None:
    """Return latest completed run for employee/date."""

    cur.execute(FIND_COMPLETED_RUN_SQL, (employee_id, task_date))
    row = cur.fetchone()
    if row is None:
        return None
    return _map_run_row(row)


def insert_run(
    cur: Cursor[object],
    *,
    employee_id: int,
    task_date: date,
    status: str,
    report_json: dict[str, object] | None,
    error: str | None,
    forced: bool,
) -> AuditRunRecord:
    """Insert audit run row and return full metadata."""

    report_payload = Jsonb(report_json) if report_json is not None else None
    cur.execute(INSERT_AUDIT_RUN_SQL, (employee_id, task_date, status, report_payload, error, forced))
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("Failed to insert audit run")
    return _map_run_row(row)


def mark_run_completed(cur: Cursor[object], run_id: UUID, report_json: dict[str, object]) -> None:
    """Persist completed status and report payload."""

    cur.execute(COMPLETE_AUDIT_RUN_SQL, (Jsonb(report_json), run_id))


def mark_run_failed(cur: Cursor[object], run_id: UUID, error: str) -> None:
    """Persist failed status with bounded error text."""

    cur.execute(FAIL_AUDIT_RUN_SQL, (error[:4000], run_id))


def fetch_prefetch_payload(cur: Cursor[object], employee_id: int, task_date: date) -> AuditPrefetchPayload:
    """Prefetch all audit inputs exactly once before Crew kickoff."""

    cur.execute(FETCH_CYCLES_SQL, (employee_id, task_date))
    cycles = cur.fetchall()

    aggregated_tasks: list[dict[str, object]] = []
    for raw_cycle in cycles:
        cycle = cast(tuple[Any, ...], raw_cycle)
        aggregated_tasks.append(
            {
                "cycle_key": str(cycle[0]),
                "canonical_text": str(cycle[1]),
                "task_category": None if cycle[2] is None else str(cycle[2]),
                "total_duration_minutes": int(cycle[3]),
                "tasks_count": int(cycle[4]),
                "is_zhdun": bool(cycle[5]),
                "avg_quality_score": None if cycle[6] is None else float(cycle[6]),
                "avg_smart_score": None if cycle[7] is None else float(cycle[7]),
            }
        )

    cur.execute(FETCH_AUDIT_METRICS_SQL, (employee_id, task_date))
    metric_row = cast(tuple[Any, ...] | None, cur.fetchone())
    if metric_row is None:
        index_of_trust_base = 0.0
        ghost_time_hours = 0.0
        none_ratio = 0.0
        non_smart_ratio = 0.0
    else:
        index_of_trust_base = float(metric_row[0])
        ghost_time_hours = float(metric_row[1])
        none_ratio = float(metric_row[2])
        non_smart_ratio = float(metric_row[3])

    return AuditPrefetchPayload(
        employee_id=employee_id,
        task_date=task_date,
        index_of_trust_base=max(0.0, min(1.0, index_of_trust_base)),
        none_time_source_ratio=max(0.0, min(1.0, none_ratio)),
        non_smart_ratio=max(0.0, min(1.0, non_smart_ratio)),
        ghost_time_hours=max(0.0, ghost_time_hours),
        aggregated_tasks=aggregated_tasks,
    )


def fetch_run_by_id(cur: Cursor[object], run_id: UUID) -> AuditRunRecord | None:
    """Return one audit run by id."""

    cur.execute(FETCH_AUDIT_RUN_SQL, (run_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return _map_run_row(row)


def insert_feedback(
    cur: Cursor[object],
    *,
    run_id: UUID,
    rating: int | None,
    comment: str | None,
    submitted_by: str | None,
) -> None:
    """Insert audit feedback row."""

    cur.execute(INSERT_AUDIT_FEEDBACK_SQL, (run_id, rating, comment, submitted_by))


def _map_run_row(row: Any) -> AuditRunRecord:
    return AuditRunRecord(
        id=row[0],
        employee_id=int(row[1]),
        task_date=row[2],
        status=str(row[3]),
        started_at=row[4],
        finished_at=row[5],
        report_json=row[6],
        forced=bool(row[7]),
    )
