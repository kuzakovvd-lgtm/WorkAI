"""Parallel-run comparison helpers for Phase 11 migration/cutover."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any

from WorkAI.common import configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.ops.models import ParallelDiffItem, ParallelDiffResult

_LOG = get_logger(__name__)

_TABLE_QUERIES: dict[str, str] = {
    "raw_tasks": "SELECT COUNT(*) FROM raw_tasks WHERE work_date = %s",
    "tasks_normalized": "SELECT COUNT(*) FROM tasks_normalized WHERE task_date = %s",
    "daily_task_assessments": "SELECT COUNT(*) FROM daily_task_assessments WHERE task_date = %s",
    "employee_daily_ghost_time": "SELECT COUNT(*) FROM employee_daily_ghost_time WHERE task_date = %s",
    "operational_cycles": "SELECT COUNT(*) FROM operational_cycles WHERE task_date = %s",
    "audit_runs": "SELECT COUNT(*) FROM audit_runs WHERE task_date = %s",
}


def run_parallel_diff(
    target_date: date,
    *,
    reference_counts: dict[str, int],
    tolerance_pct: float = 5.0,
    settings: Settings | None = None,
) -> ParallelDiffResult:
    """Compare reference counts (v1) against current DB counts (v2 candidate)."""

    resolved = settings or get_settings()
    configure_logging(resolved)
    init_db(resolved)
    try:
        candidate_counts = _fetch_candidate_counts(target_date)
    finally:
        close_db()

    return compare_counts(
        target_date=target_date,
        reference_counts=reference_counts,
        candidate_counts=candidate_counts,
        tolerance_pct=tolerance_pct,
    )


def compare_counts(
    *,
    target_date: date,
    reference_counts: dict[str, int],
    candidate_counts: dict[str, int],
    tolerance_pct: float,
) -> ParallelDiffResult:
    """Pure comparison helper used by runtime and unit tests."""

    diffs: list[ParallelDiffItem] = []
    violations: list[str] = []

    table_names = sorted(set(reference_counts) | set(candidate_counts))
    for table in table_names:
        reference_count = int(reference_counts.get(table, 0))
        candidate_count = int(candidate_counts.get(table, 0))
        delta = candidate_count - reference_count

        if reference_count == 0:
            delta_pct = 0.0 if candidate_count == 0 else 100.0
        else:
            delta_pct = abs(delta) * 100.0 / reference_count

        within_tolerance = delta_pct <= tolerance_pct
        if not within_tolerance:
            violations.append(table)

        diffs.append(
            ParallelDiffItem(
                table=table,
                reference_count=reference_count,
                candidate_count=candidate_count,
                delta=delta,
                delta_pct=round(delta_pct, 4),
                within_tolerance=within_tolerance,
            )
        )

    result = ParallelDiffResult(
        target_date=target_date,
        tolerance_pct=tolerance_pct,
        reference_counts={k: int(v) for k, v in sorted(reference_counts.items())},
        candidate_counts={k: int(v) for k, v in sorted(candidate_counts.items())},
        diffs=diffs,
        violations=sorted(violations),
        generated_at=datetime.now(UTC),
    )

    _LOG.info(
        "parallel_diff_completed",
        target_date=target_date.isoformat(),
        tolerance_pct=tolerance_pct,
        tables=len(diffs),
        violations=len(result.violations),
    )
    return result


def parallel_diff_to_dict(result: ParallelDiffResult) -> dict[str, Any]:
    """Serialize comparison result for JSON CLI output."""

    return {
        "target_date": result.target_date.isoformat(),
        "tolerance_pct": result.tolerance_pct,
        "reference_counts": result.reference_counts,
        "candidate_counts": result.candidate_counts,
        "violations": result.violations,
        "generated_at": result.generated_at.isoformat(),
        "diffs": [asdict(item) for item in result.diffs],
    }


def _fetch_candidate_counts(target_date: date) -> dict[str, int]:
    counts: dict[str, int] = {}
    with connection() as conn, conn.cursor() as cur:
        for table, sql in _TABLE_QUERIES.items():
            cur.execute(sql, (target_date,))
            value = cur.fetchone()
            counts[table] = 0 if value is None else int(value[0])
    return counts

