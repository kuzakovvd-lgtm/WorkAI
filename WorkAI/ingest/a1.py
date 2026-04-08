"""A1 notation parsing and conversion helpers."""

from __future__ import annotations

import re

from WorkAI.ingest.models import A1RangeSpec

_CELL_RE = re.compile(r"^([A-Za-z]+)([1-9][0-9]*)$")


def col_to_index(col: str) -> int:
    """Convert spreadsheet column label (A, Z, AA) to 1-based index."""

    normalized = col.strip().upper()
    if normalized == "" or not normalized.isalpha():
        raise ValueError(f"Invalid column label: {col!r}")

    result = 0
    for char in normalized:
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result


def index_to_col(index: int) -> str:
    """Convert 1-based column index to spreadsheet column label."""

    if index <= 0:
        raise ValueError("Column index must be positive")

    current = index
    result: list[str] = []
    while current > 0:
        current -= 1
        result.append(chr(ord("A") + (current % 26)))
        current //= 26
    return "".join(reversed(result))


def cell_to_a1(row: int, col: int) -> str:
    """Return A1 cell reference for 1-based row/col indexes."""

    if row <= 0:
        raise ValueError("Row index must be positive")
    return f"{index_to_col(col)}{row}"


def _parse_cell(cell: str) -> tuple[int, int]:
    matched = _CELL_RE.match(cell)
    if matched is None:
        raise ValueError(
            "Invalid A1 range. Use bounded ranges like 'Sheet1!A1:C30'; "
            "use bounded ranges to avoid huge ingest."
        )

    col_label, row_number = matched.groups()
    return int(row_number), col_to_index(col_label)


def parse_a1_range(a1: str) -> A1RangeSpec:
    """Parse bounded A1 range with mandatory sheet title."""

    if "!" not in a1:
        raise ValueError("A1 range must include sheet title, e.g. 'Sheet1!A1:C3'")

    sheet_title_raw, range_part = a1.split("!", 1)
    sheet_title = sheet_title_raw.strip()
    if sheet_title.startswith("'") and sheet_title.endswith("'") and len(sheet_title) >= 2:
        sheet_title = sheet_title[1:-1].replace("''", "'")

    if sheet_title == "":
        raise ValueError("Sheet title in A1 range cannot be empty")

    if ":" not in range_part:
        raise ValueError(
            "Unbounded or invalid A1 range. Use bounded ranges like 'Sheet1!A1:C30'; "
            "use bounded ranges to avoid huge ingest."
        )

    start_cell, end_cell = [part.strip() for part in range_part.split(":", 1)]
    if start_cell == "" or end_cell == "":
        raise ValueError(
            "Invalid A1 range bounds. Use bounded ranges like 'Sheet1!A1:C30'; "
            "use bounded ranges to avoid huge ingest."
        )

    start_row, start_col = _parse_cell(start_cell)
    end_row, end_col = _parse_cell(end_cell)

    if end_row < start_row or end_col < start_col:
        raise ValueError("A1 range end must be greater than or equal to start")

    return A1RangeSpec(
        sheet_title=sheet_title,
        start_row=start_row,
        start_col=start_col,
        end_row=end_row,
        end_col=end_col,
    )
