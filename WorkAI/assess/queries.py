"""SQL helpers for assess ghost-time, scoring, and aggregation steps."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any, cast

from psycopg import Cursor

from WorkAI.assess.models import (
    AssessmentTaskForAggregation,
    DailyTaskAssessmentRow,
    EmployeeDailyGhostTimeRow,
    EmployeeDayKey,
    EmployeeDayMetrics,
    NormalizedTaskForScoring,
    OperationalCycleRow,
)

LIST_EMPLOYEE_DAY_KEYS_SQL = """
SELECT DISTINCT
    employee_id,
    task_date
FROM tasks_normalized
WHERE task_date = %s
ORDER BY employee_id
"""

FETCH_DAY_METRICS_SQL = """
SELECT
    COALESCE(SUM(COALESCE(duration_minutes, 0)), 0)::int AS logged_minutes,
    COUNT(*)::int AS total_tasks,
    SUM(CASE WHEN time_source = 'none' THEN 1 ELSE 0 END)::int AS none_count,
    SUM(CASE WHEN result_confirmed = false THEN 1 ELSE 0 END)::int AS unconfirmed_count
FROM tasks_normalized
WHERE task_date = %s
  AND employee_id = %s
"""

UPSERT_GHOST_TIME_SQL = """
INSERT INTO employee_daily_ghost_time (
    employee_id,
    task_date,
    workday_minutes,
    logged_minutes,
    ghost_minutes,
    index_of_trust_base,
    computed_at
)
VALUES (%s, %s, %s, %s, %s, %s, now())
ON CONFLICT (employee_id, task_date)
DO UPDATE SET
    workday_minutes = EXCLUDED.workday_minutes,
    logged_minutes = EXCLUDED.logged_minutes,
    ghost_minutes = EXCLUDED.ghost_minutes,
    index_of_trust_base = EXCLUDED.index_of_trust_base,
    computed_at = now()
"""

FETCH_SCORING_TASKS_BY_DATE_SQL = """
SELECT
    id,
    employee_id,
    task_date,
    duration_minutes,
    time_source,
    is_smart,
    is_micro,
    result_confirmed,
    is_zhdun
FROM tasks_normalized
WHERE task_date = %s
ORDER BY employee_id, id
"""

FETCH_SCORING_TASKS_BY_EMPLOYEE_DAY_SQL = """
SELECT
    id,
    employee_id,
    task_date,
    duration_minutes,
    time_source,
    is_smart,
    is_micro,
    result_confirmed,
    is_zhdun
FROM tasks_normalized
WHERE employee_id = %s
  AND task_date = %s
ORDER BY id
"""

UPSERT_DAILY_TASK_ASSESSMENT_SQL = """
INSERT INTO daily_task_assessments (
    normalized_task_id,
    employee_id,
    task_date,
    norm_minutes,
    delta_minutes,
    quality_score,
    smart_score,
    assessed_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (normalized_task_id)
DO UPDATE SET
    employee_id = EXCLUDED.employee_id,
    task_date = EXCLUDED.task_date,
    norm_minutes = EXCLUDED.norm_minutes,
    delta_minutes = EXCLUDED.delta_minutes,
    quality_score = EXCLUDED.quality_score,
    smart_score = EXCLUDED.smart_score,
    assessed_at = now()
"""

FETCH_AGGREGATION_INPUT_BY_DATE_SQL = """
SELECT
    tn.id,
    tn.employee_id,
    tn.task_date,
    tn.spreadsheet_id,
    tn.sheet_title,
    tn.row_idx,
    tn.col_idx,
    tn.line_no,
    tn.canonical_text,
    tn.task_category,
    tn.duration_minutes,
    tn.is_micro,
    tn.is_zhdun,
    dta.quality_score,
    dta.smart_score
FROM tasks_normalized AS tn
LEFT JOIN daily_task_assessments AS dta
  ON dta.normalized_task_id = tn.id
WHERE tn.task_date = %s
ORDER BY
    tn.employee_id,
    tn.task_date,
    tn.sheet_title,
    tn.row_idx,
    tn.col_idx,
    tn.line_no,
    tn.id
"""

DELETE_OPERATIONAL_CYCLES_FOR_EMPLOYEE_DAY_SQL = """
DELETE FROM operational_cycles
WHERE employee_id = %s
  AND task_date = %s
"""

UPSERT_OPERATIONAL_CYCLE_SQL = """
INSERT INTO operational_cycles (
    employee_id,
    task_date,
    cycle_key,
    canonical_text,
    task_category,
    total_duration_minutes,
    tasks_count,
    is_zhdun,
    avg_quality_score,
    avg_smart_score,
    created_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (employee_id, task_date, cycle_key)
DO UPDATE SET
    canonical_text = EXCLUDED.canonical_text,
    task_category = EXCLUDED.task_category,
    total_duration_minutes = EXCLUDED.total_duration_minutes,
    tasks_count = EXCLUDED.tasks_count,
    is_zhdun = EXCLUDED.is_zhdun,
    avg_quality_score = EXCLUDED.avg_quality_score,
    avg_smart_score = EXCLUDED.avg_smart_score,
    created_at = now()
"""


def list_employee_day_keys(cur: Cursor[object], target_date: date) -> list[EmployeeDayKey]:
    """Return employee/day keys present in tasks_normalized for target date."""

    cur.execute(LIST_EMPLOYEE_DAY_KEYS_SQL, (target_date,))
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return [EmployeeDayKey(employee_id=int(row[0]), task_date=cast(date, row[1])) for row in rows]


def fetch_employee_day_metrics(
    cur: Cursor[object],
    employee_id: int,
    target_date: date,
) -> EmployeeDayMetrics:
    """Return aggregate metrics for one employee/day."""

    cur.execute(FETCH_DAY_METRICS_SQL, (target_date, employee_id))
    row = cast(tuple[Any, ...] | None, cur.fetchone())
    if row is None:
        return EmployeeDayMetrics(logged_minutes=0, total_tasks=0, none_count=0, unconfirmed_count=0)

    return EmployeeDayMetrics(
        logged_minutes=int(row[0]),
        total_tasks=int(row[1]),
        none_count=int(row[2]),
        unconfirmed_count=int(row[3]),
    )


def upsert_employee_daily_ghost_time(
    cur: Cursor[object],
    row: EmployeeDailyGhostTimeRow,
) -> None:
    """Upsert one assess ghost-time row by natural key."""

    cur.execute(
        UPSERT_GHOST_TIME_SQL,
        (
            row.employee_id,
            row.task_date,
            row.workday_minutes,
            row.logged_minutes,
            row.ghost_minutes,
            row.index_of_trust_base,
        ),
    )


def upsert_employee_daily_ghost_time_batch(
    cur: Cursor[object],
    rows: Sequence[EmployeeDailyGhostTimeRow],
) -> None:
    """Upsert rows in batch using executemany."""

    if not rows:
        return

    cur.executemany(
        UPSERT_GHOST_TIME_SQL,
        [
            (
                row.employee_id,
                row.task_date,
                row.workday_minutes,
                row.logged_minutes,
                row.ghost_minutes,
                row.index_of_trust_base,
            )
            for row in rows
        ],
    )


def fetch_scoring_tasks_by_date(cur: Cursor[object], target_date: date) -> list[NormalizedTaskForScoring]:
    """Return tasks_normalized rows for task-level scoring at specific date."""

    cur.execute(FETCH_SCORING_TASKS_BY_DATE_SQL, (target_date,))
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return [_row_to_scoring_task(row) for row in rows]


def fetch_scoring_tasks_by_employee_day(
    cur: Cursor[object],
    employee_id: int,
    target_date: date,
) -> list[NormalizedTaskForScoring]:
    """Return scoring tasks for one employee/day partition."""

    cur.execute(FETCH_SCORING_TASKS_BY_EMPLOYEE_DAY_SQL, (employee_id, target_date))
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return [_row_to_scoring_task(row) for row in rows]


def upsert_daily_task_assessment(cur: Cursor[object], row: DailyTaskAssessmentRow) -> None:
    """Upsert one daily_task_assessments row."""

    cur.execute(
        UPSERT_DAILY_TASK_ASSESSMENT_SQL,
        (
            row.normalized_task_id,
            row.employee_id,
            row.task_date,
            row.norm_minutes,
            row.delta_minutes,
            row.quality_score,
            row.smart_score,
        ),
    )


def upsert_daily_task_assessments_batch(
    cur: Cursor[object],
    rows: Sequence[DailyTaskAssessmentRow],
) -> None:
    """Batch UPSERT task scoring rows by normalized_task_id."""

    if not rows:
        return

    cur.executemany(
        UPSERT_DAILY_TASK_ASSESSMENT_SQL,
        [
            (
                row.normalized_task_id,
                row.employee_id,
                row.task_date,
                row.norm_minutes,
                row.delta_minutes,
                row.quality_score,
                row.smart_score,
            )
            for row in rows
        ],
    )


def fetch_aggregation_input_by_date(
    cur: Cursor[object],
    target_date: date,
) -> list[AssessmentTaskForAggregation]:
    """Fetch normalized tasks joined with scoring values for aggregation."""

    cur.execute(FETCH_AGGREGATION_INPUT_BY_DATE_SQL, (target_date,))
    rows = cast(list[tuple[Any, ...]], cur.fetchall())
    return [_row_to_aggregation_input(row) for row in rows]


def delete_operational_cycles_for_employee_day(
    cur: Cursor[object],
    employee_id: int,
    target_date: date,
) -> None:
    """Delete operational cycles for one employee/day partition."""

    cur.execute(DELETE_OPERATIONAL_CYCLES_FOR_EMPLOYEE_DAY_SQL, (employee_id, target_date))


def upsert_operational_cycles_batch(
    cur: Cursor[object],
    rows: Sequence[OperationalCycleRow],
) -> None:
    """Batch upsert operational cycles rows."""

    if not rows:
        return

    cur.executemany(
        UPSERT_OPERATIONAL_CYCLE_SQL,
        [
            (
                row.employee_id,
                row.task_date,
                row.cycle_key,
                row.canonical_text,
                row.task_category,
                row.total_duration_minutes,
                row.tasks_count,
                row.is_zhdun,
                row.avg_quality_score,
                row.avg_smart_score,
            )
            for row in rows
        ],
    )


def _row_to_scoring_task(row: tuple[Any, ...]) -> NormalizedTaskForScoring:
    return NormalizedTaskForScoring(
        normalized_task_id=int(row[0]),
        employee_id=int(row[1]),
        task_date=cast(date, row[2]),
        duration_minutes=None if row[3] is None else int(row[3]),
        time_source=str(row[4]),
        is_smart=bool(row[5]),
        is_micro=bool(row[6]),
        result_confirmed=bool(row[7]),
        is_zhdun=bool(row[8]),
    )


def _row_to_aggregation_input(row: tuple[Any, ...]) -> AssessmentTaskForAggregation:
    quality_score = None if row[13] is None else cast(Decimal, row[13])
    smart_score = None if row[14] is None else cast(Decimal, row[14])
    return AssessmentTaskForAggregation(
        normalized_task_id=int(row[0]),
        employee_id=int(row[1]),
        task_date=cast(date, row[2]),
        spreadsheet_id=str(row[3]),
        sheet_title=str(row[4]),
        row_idx=int(row[5]),
        col_idx=int(row[6]),
        line_no=int(row[7]),
        canonical_text=str(row[8]),
        task_category=None if row[9] is None else str(row[9]),
        duration_minutes=None if row[10] is None else int(row[10]),
        is_micro=bool(row[11]),
        is_zhdun=bool(row[12]),
        quality_score=quality_score,
        smart_score=smart_score,
    )
