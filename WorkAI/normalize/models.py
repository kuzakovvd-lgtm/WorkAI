"""Typed models for normalize layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass(frozen=True)
class RawTask:
    """Raw task row loaded from raw_tasks table."""

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


@dataclass(frozen=True)
class NormalizedTaskRow:
    """Normalized row prepared for tasks_normalized insert."""

    spreadsheet_id: str
    sheet_title: str
    row_idx: int
    col_idx: int
    line_no: int
    work_date: date
    employee_name_raw: str
    employee_name_norm: str
    employee_match_method: str
    task_text_raw: str
    task_text_norm: str
    time_start: time | None
    time_end: time | None
    duration_minutes: int | None
    category_code: str | None
    source_cell_ingested_at: datetime


@dataclass
class NormalizeStats:
    """Counters collected during normalize execution."""

    sheets_processed: int = 0
    raw_rows_read: int = 0
    rows_emitted: int = 0
    rows_skipped: int = 0
    rows_failed: int = 0
    fuzzy_matches: int = 0
    alias_matches: int = 0
    duration_extracted_count: int = 0
    category_assigned_count: int = 0
