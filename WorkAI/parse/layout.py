"""Layout inference helpers for sheet matrix parsing."""

from __future__ import annotations

from datetime import date

from WorkAI.parse.date_parse import parse_work_date
from WorkAI.parse.models import SheetCell


def build_date_by_col(
    cells: list[SheetCell],
    header_row_idx: int,
    employee_col_idx: int,
    formats: list[str],
) -> dict[int, date]:
    """Build column->date mapping from header row values."""

    date_by_col: dict[int, date] = {}
    for cell in cells:
        if cell.row_idx != header_row_idx:
            continue
        if cell.col_idx <= employee_col_idx:
            continue
        if cell.value_text is None:
            continue

        parsed = parse_work_date(cell.value_text, formats)
        if parsed is not None:
            date_by_col[cell.col_idx] = parsed

    return date_by_col


def build_employee_by_row(
    cells: list[SheetCell],
    header_row_idx: int,
    employee_col_idx: int,
) -> dict[int, str]:
    """Build row->employee mapping from employee column values."""

    employee_by_row: dict[int, str] = {}
    for cell in cells:
        if cell.row_idx <= header_row_idx:
            continue
        if cell.col_idx != employee_col_idx:
            continue
        if cell.value_text is None:
            continue

        employee_name = cell.value_text.strip()
        if employee_name:
            employee_by_row[cell.row_idx] = employee_name

    return employee_by_row
