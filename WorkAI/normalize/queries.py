"""SQL helpers for normalize runner."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time

from psycopg import Cursor

from WorkAI.normalize.models import NormalizedTaskRow, RawTask

SELECT_RAW_TASKS_SQL = """
SELECT
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
    category_code,
    source_cell_ingested_at,
    normalized_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
"""


def fetch_raw_tasks(
    cursor: Cursor[tuple[str, str, int, int, str, datetime, str | None, date | None, int, str]],
    spreadsheet_id: str,
) -> list[RawTask]:
    """Load raw_tasks rows for a spreadsheet."""

    cursor.execute(SELECT_RAW_TASKS_SQL, (spreadsheet_id,))
    rows = cursor.fetchall()

    return [
        RawTask(
            spreadsheet_id=str(row[0]),
            sheet_title=str(row[1]),
            row_idx=int(row[2]),
            col_idx=int(row[3]),
            cell_a1=str(row[4]),
            cell_ingested_at=row[5],
            employee_name_raw=None if row[6] is None else str(row[6]),
            work_date=row[7],
            line_no=int(row[8]),
            line_text=str(row[9]),
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

    params: list[
        tuple[
            str,
            str,
            int,
            int,
            int,
            date,
            str,
            str,
            str,
            str,
            str,
            time | None,
            time | None,
            int | None,
            str | None,
            datetime,
        ]
    ] = [
        (
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
            row.category_code,
            row.source_cell_ingested_at,
        )
        for row in rows
    ]
    if params:
        cursor.executemany(INSERT_TASKS_NORMALIZED_SQL, params)
