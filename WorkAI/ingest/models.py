"""Typed models for ingest layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class A1RangeSpec:
    """Parsed A1 range with explicit bounded coordinates."""

    sheet_title: str
    start_row: int
    start_col: int
    end_row: int
    end_col: int


@dataclass(frozen=True)
class ValueRange:
    """Subset of Google Sheets API ValueRange payload."""

    range: str
    values: list[list[Any]]


@dataclass(frozen=True)
class CellValue:
    """Cell value prepared for DB insert."""

    spreadsheet_id: str
    sheet_title: str
    row_idx: int
    col_idx: int
    a1: str
    value_text: str
