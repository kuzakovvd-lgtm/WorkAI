"""SQL helpers for normalize runner."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from psycopg import Cursor

from WorkAI.normalize.models import NormalizedTaskRow, RawTask

SELECT_RAW_TASKS_SQL = """
SELECT
    raw_task_id,
    spreadsheet_id,
    sheet_title,
    row_idx,
    col_idx,
    cell_a1,
    cell_ingested_at,
    employee_name_raw,
    work_date,
    line_no,
    line_text
FROM raw_tasks
WHERE spreadsheet_id = %s
ORDER BY sheet_title, row_idx, col_idx, line_no
"""

DELETE_TASKS_NORMALIZED_FOR_SHEET_DATE_SQL = """
DELETE FROM tasks_normalized
WHERE spreadsheet_id = %s AND sheet_title = %s AND work_date = %s
"""

INSERT_TASKS_NORMALIZED_SQL = """
INSERT INTO tasks_normalized (
    raw_task_id,
    task_date,
    employee_id,
    spreadsheet_id,
    sheet_title,
    row_idx,
    col_idx,
    line_no,
    work_date,
    employee_name_raw,
    employee_name_norm,
    employee_match_method,
    task_text_raw,
    task_text_norm,
    time_start,
    time_end,
    duration_minutes,
    time_source,
    is_smart,
    is_micro,
    result_confirmed,
    is_zhdun,
    category_code,
    task_category,
    canonical_text,
    source_cell_ingested_at,
    normalized_at
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
)
"""


def fetch_raw_tasks(
    cursor: Cursor[tuple[int, str, str, int, int, str, datetime, str | None, date | None, int, str]],
    spreadsheet_id: str,
) -> list[RawTask]:
    """Load raw_tasks rows for a spreadsheet."""

    cursor.execute(SELECT_RAW_TASKS_SQL, (spreadsheet_id,))
    rows = cursor.fetchall()

    return [
        RawTask(
            raw_task_id=int(row[0]),
            spreadsheet_id=str(row[1]),
            sheet_title=str(row[2]),
            row_idx=int(row[3]),
            col_idx=int(row[4]),
            cell_a1=str(row[5]),
            cell_ingested_at=row[6],
            employee_name_raw=None if row[7] is None else str(row[7]),
            work_date=row[8],
            line_no=int(row[9]),
            line_text=str(row[10]),
        )
        for row in rows
    ]


def delete_tasks_normalized_for_sheet_date(
    cursor: Cursor[tuple[object, ...]],
    spreadsheet_id: str,
    sheet_title: str,
    work_date: date,
) -> None:
    """Delete old normalized rows for one sheet and date before full-refresh insert."""

    cursor.execute(DELETE_TASKS_NORMALIZED_FOR_SHEET_DATE_SQL, (spreadsheet_id, sheet_title, work_date))


def insert_tasks_normalized_batch(
    cursor: Cursor[tuple[object, ...]],
    rows: Sequence[NormalizedTaskRow],
) -> None:
    """Insert normalized rows using executemany."""

    params: list[tuple[object, ...]] = [
        (
            row.raw_task_id,
            row.task_date,
            row.employee_id,
            row.spreadsheet_id,
            row.sheet_title,
            row.row_idx,
            row.col_idx,
            row.line_no,
            row.work_date,
            row.employee_name_raw,
            row.employee_name_norm,
            row.employee_match_method,
            row.task_text_raw,
            row.task_text_norm,
            row.time_start,
            row.time_end,
            row.duration_minutes,
            row.time_source,
            row.is_smart,
            row.is_micro,
            row.result_confirmed,
            row.is_zhdun,
            row.category_code,
            row.task_category,
            row.canonical_text,
            row.source_cell_ingested_at,
        )
        for row in rows
    ]
    if params:
        cursor.executemany(INSERT_TASKS_NORMALIZED_SQL, params)


UPSERT_EMPLOYEE_SQL = """
INSERT INTO employees (employee_name_norm)
VALUES (%s)
ON CONFLICT (employee_name_norm) DO UPDATE
SET employee_name_norm = EXCLUDED.employee_name_norm
RETURNING employee_id
"""


def get_or_create_employee_id(
    cursor: Cursor[tuple[int]],
    employee_name_norm: str,
) -> int:
    """Return stable employee_id for canonical employee name."""

    cursor.execute(UPSERT_EMPLOYEE_SQL, (employee_name_norm,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Failed to resolve employee_id")
    return int(row[0])
