from datetime import UTC, datetime

from WorkAI.parse.layout import build_date_by_col, build_employee_by_row
from WorkAI.parse.models import SheetCell


def _cell(row_idx: int, col_idx: int, value_text: str | None) -> SheetCell:
    return SheetCell(
        spreadsheet_id="spreadsheet-1",
        sheet_title="Sheet1",
        row_idx=row_idx,
        col_idx=col_idx,
        a1=f"R{row_idx}C{col_idx}",
        value_text=value_text,
        ingested_at=datetime.now(UTC),
    )


def test_build_date_by_col() -> None:
    cells = [
        _cell(1, 1, "Employee"),
        _cell(1, 2, "2026-04-07"),
        _cell(1, 3, "08.04.2026"),
        _cell(2, 2, "not header"),
    ]

    date_by_col = build_date_by_col(cells, header_row_idx=1, employee_col_idx=1, formats=["%Y-%m-%d", "%d.%m.%Y"])

    assert date_by_col[2].isoformat() == "2026-04-07"
    assert date_by_col[3].isoformat() == "2026-04-08"


def test_build_employee_by_row() -> None:
    cells = [
        _cell(1, 1, "Employee"),
        _cell(2, 1, "Alice"),
        _cell(3, 1, " Bob "),
        _cell(3, 2, "wrong col"),
    ]

    employee_by_row = build_employee_by_row(cells, header_row_idx=1, employee_col_idx=1)

    assert employee_by_row == {2: "Alice", 3: "Bob"}
