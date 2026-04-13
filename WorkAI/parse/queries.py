"""SQL helpers for parse runner."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from psycopg import Cursor

from WorkAI.parse.models import RawTaskRow, SheetCell

SELECT_SHEET_CELLS_SQL = """
SELECT
    spreadsheet_id,
    sheet_title,
    row_idx,
    col_idx,
    a1,
    value_text,
    ingested_at
FROM sheet_cells
WHERE spreadsheet_id = %s
ORDER BY sheet_title, row_idx, col_idx
"""

DELETE_RAW_TASKS_FOR_SHEET_SQL = """
DELETE FROM raw_tasks
WHERE spreadsheet_id = %s AND sheet_title = %s
"""

SELECT_RAW_TASK_DATES_FOR_SHEET_SQL = """
SELECT DISTINCT work_date
FROM raw_tasks
WHERE spreadsheet_id = %s
  AND sheet_title = %s
  AND work_date IS NOT NULL
ORDER BY work_date
"""

DELETE_RAW_TASKS_FOR_SHEET_DATES_SQL = """
DELETE FROM raw_tasks
WHERE spreadsheet_id = %s
  AND sheet_title = %s
  AND work_date = ANY(%s::date[])
"""

DELETE_RAW_TASKS_FOR_SHEET_NULL_DATE_SQL = """
DELETE FROM raw_tasks
WHERE spreadsheet_id = %s
  AND sheet_title = %s
  AND work_date IS NULL
"""

DELETE_TASKS_NORMALIZED_FOR_SHEET_DATES_SQL = """
DELETE FROM tasks_normalized
WHERE spreadsheet_id = %s
  AND sheet_title = %s
  AND work_date = ANY(%s::date[])
"""

INSERT_RAW_TASK_SQL = """
INSERT INTO raw_tasks (
    spreadsheet_id,
    sheet_title,
    row_idx,
    col_idx,
    cell_a1,
    cell_ingested_at,
    employee_name_raw,
    work_date,
    line_no,
    line_text,
    parsed_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
"""


def fetch_sheet_cells(
    cursor: Cursor[tuple[str, str, int, int, str, str | None, datetime]],
    spreadsheet_id: str,
) -> list[SheetCell]:
    """Load sheet_cells rows for spreadsheet."""

    cursor.execute(SELECT_SHEET_CELLS_SQL, (spreadsheet_id,))
    rows = cursor.fetchall()

    return [
        SheetCell(
            spreadsheet_id=str(row[0]),
            sheet_title=str(row[1]),
            row_idx=int(row[2]),
            col_idx=int(row[3]),
            a1=str(row[4]),
            value_text=None if row[5] is None else str(row[5]),
            ingested_at=row[6],  # psycopg returns datetime
        )
        for row in rows
    ]


def delete_raw_tasks_for_sheet(
    cursor: Cursor[tuple[object, ...]],
    spreadsheet_id: str,
    sheet_title: str,
) -> None:
    """Delete old raw_tasks for one sheet before full-refresh insert."""

    cursor.execute(DELETE_RAW_TASKS_FOR_SHEET_SQL, (spreadsheet_id, sheet_title))


def fetch_raw_task_dates_for_sheet(
    cursor: Cursor[tuple[date]],
    spreadsheet_id: str,
    sheet_title: str,
) -> list[date]:
    """Return existing raw_tasks date scope for one sheet."""

    cursor.execute(SELECT_RAW_TASK_DATES_FOR_SHEET_SQL, (spreadsheet_id, sheet_title))
    return [row[0] for row in cursor.fetchall()]


def delete_tasks_normalized_for_sheet_dates(
    cursor: Cursor[tuple[object, ...]],
    spreadsheet_id: str,
    sheet_title: str,
    work_dates: Sequence[date],
) -> None:
    """Delete dependent normalized rows for one sheet/date scope."""

    if not work_dates:
        return
    cursor.execute(
        DELETE_TASKS_NORMALIZED_FOR_SHEET_DATES_SQL,
        (spreadsheet_id, sheet_title, list(work_dates)),
    )


def delete_raw_tasks_for_sheet_dates(
    cursor: Cursor[tuple[object, ...]],
    spreadsheet_id: str,
    sheet_title: str,
    work_dates: Sequence[date],
) -> None:
    """Delete raw_tasks for one sheet/date scope."""

    if not work_dates:
        return
    cursor.execute(
        DELETE_RAW_TASKS_FOR_SHEET_DATES_SQL,
        (spreadsheet_id, sheet_title, list(work_dates)),
    )


def delete_raw_tasks_for_sheet_null_date(
    cursor: Cursor[tuple[object, ...]],
    spreadsheet_id: str,
    sheet_title: str,
) -> None:
    """Delete raw_tasks for one sheet where work_date is NULL."""

    cursor.execute(DELETE_RAW_TASKS_FOR_SHEET_NULL_DATE_SQL, (spreadsheet_id, sheet_title))


def insert_raw_tasks_batch(
    cursor: Cursor[tuple[object, ...]],
    rows: Sequence[RawTaskRow],
) -> None:
    """Insert parsed raw task rows using executemany."""

    params = [
        (
            row.spreadsheet_id,
            row.sheet_title,
            row.row_idx,
            row.col_idx,
            row.cell_a1,
            row.cell_ingested_at,
            row.employee_name_raw,
            row.work_date,
            row.line_no,
            row.line_text,
        )
        for row in rows
    ]
    if params:
        cursor.executemany(INSERT_RAW_TASK_SQL, params)
