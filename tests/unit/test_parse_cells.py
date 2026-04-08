from datetime import UTC, datetime

from WorkAI.config import ParseSettings
from WorkAI.parse.models import SheetCell
from WorkAI.parse.parser import parse_cells


def _cell(row_idx: int, col_idx: int, value_text: str | None, a1: str) -> SheetCell:
    return SheetCell(
        spreadsheet_id="spreadsheet-1",
        sheet_title="Sheet1",
        row_idx=row_idx,
        col_idx=col_idx,
        a1=a1,
        value_text=value_text,
        ingested_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
    )


def test_parse_cells_matrix() -> None:
    cells = [
        _cell(1, 1, "Employee", "A1"),
        _cell(1, 2, "2026-04-08", "B1"),
        _cell(2, 1, "Alice", "A2"),
        _cell(2, 2, "Task one\n\nTask two", "B2"),
    ]

    settings = ParseSettings(
        enabled=True,
        header_row_idx=1,
        employee_col_idx=1,
        date_formats=["%Y-%m-%d"],
    )

    rows, stats = parse_cells(cells, settings)

    assert len(rows) == 2
    assert rows[0].employee_name_raw == "Alice"
    assert rows[0].work_date is not None
    assert rows[0].line_no == 1
    assert rows[0].line_text == "Task one"
    assert rows[1].line_no == 2
    assert rows[1].line_text == "Task two"

    assert stats.sheets_processed == 1
    assert stats.cells_read == 4
    assert stats.cells_parsed == 1
    assert stats.tasks_emitted == 2
    assert stats.cells_skipped_missing_date == 0
    assert stats.cells_skipped_missing_employee == 0
