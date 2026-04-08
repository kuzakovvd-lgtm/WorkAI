"""Typed models for parse layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class SheetCell:
    """Raw ingested sheet cell from sheet_cells table."""

    spreadsheet_id: str
    sheet_title: str
    row_idx: int
    col_idx: int
    a1: str
    value_text: str | None
    ingested_at: datetime


@dataclass(frozen=True)
class RawTaskRow:
    """Parsed row prepared for raw_tasks insert."""

    spreadsheet_id: str
    sheet_title: str
    row_idx: int
    col_idx: int
    cell_a1: str
    cell_ingested_at: datetime
    employee_name_raw: str | None
    work_date: date | None
    line_no: int
    line_text: str


@dataclass
class ParseStats:
    """Counters collected during parse execution."""

    sheets_processed: int = 0
    cells_read: int = 0
    cells_parsed: int = 0
    tasks_emitted: int = 0
    cells_skipped_missing_date: int = 0
    cells_skipped_missing_employee: int = 0
    cells_failed: int = 0
