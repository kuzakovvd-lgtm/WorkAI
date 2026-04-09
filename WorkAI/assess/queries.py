"""SQL helpers for assess ghost-time step."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any, cast

from psycopg import Cursor

from WorkAI.assess.models import EmployeeDailyGhostTimeRow, EmployeeDayKey, EmployeeDayMetrics

EMPLOYEE_ID_EXPR = "(mod(abs(hashtextextended(employee_name_norm, 0)), 2147483647) + 1)::int"
# TODO(TZ §5.1): replace derived employee_id mapping with canonical employee dimension.

LIST_EMPLOYEE_DAY_KEYS_SQL = f"""
SELECT DISTINCT
    {EMPLOYEE_ID_EXPR} AS employee_id,
    work_date
FROM tasks_normalized
WHERE work_date = %s
ORDER BY employee_id
"""

FETCH_DAY_METRICS_SQL = f"""
SELECT
    COALESCE(SUM(COALESCE(duration_minutes, 0)), 0)::int AS logged_minutes,
    COUNT(*)::int AS total_tasks,
    SUM(CASE WHEN duration_minutes IS NULL THEN 1 ELSE 0 END)::int AS none_count,
    SUM(CASE WHEN duration_minutes IS NULL THEN 1 ELSE 0 END)::int AS unconfirmed_count
FROM tasks_normalized
WHERE work_date = %s
  AND {EMPLOYEE_ID_EXPR} = %s
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
