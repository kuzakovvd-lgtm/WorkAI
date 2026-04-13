from __future__ import annotations

from datetime import UTC, date, datetime

from WorkAI.config import ParseSettings
from WorkAI.parse.models import SheetCell
from WorkAI.parse.parser import (
    _detect_task_columns,
    _is_non_task_text,
    _parse_weekly_board_cells,
    _resolve_week_year,
    parse_cells,
)


def _cell(
    row_idx: int,
    col_idx: int,
    value_text: str | None,
    *,
    sheet_title: str = "Alice",
) -> SheetCell:
    return SheetCell(
        spreadsheet_id="sheet-1",
        sheet_title=sheet_title,
        row_idx=row_idx,
        col_idx=col_idx,
        a1=f"R{row_idx}C{col_idx}",
        value_text=value_text,
        ingested_at=datetime(2026, 4, 10, 10, 0, tzinfo=UTC),
    )


def _settings() -> ParseSettings:
    return ParseSettings(
        enabled=True,
        header_row_idx=1,
        employee_col_idx=1,
        date_formats=["%Y-%m-%d", "%d.%m.%Y"],
    )


def test_parse_cells_uses_weekly_board_fallback_and_resets_skip_counters() -> None:
    cells = [
        _cell(1, 1, "07.04 - 13.04"),
        _cell(11, 10, "Задача"),
        _cell(11, 14, "ЗАДАЧА"),
        _cell(12, 10, "Task one\nTask two"),
        _cell(12, 14, "в работе 2"),
        _cell(13, 5, "2026"),
    ]

    rows, stats = parse_cells(cells, _settings())

    assert len(rows) == 2
    assert rows[0].line_text == "Task one"
    assert rows[1].line_text == "Task two"
    assert rows[0].employee_name_raw == "Alice"
    assert rows[0].work_date == date(2026, 4, 7)

    # Strict mode reports missing date/employee, but fallback success clears this noise.
    assert stats.cells_skipped_missing_date == 0
    assert stats.cells_skipped_missing_employee == 0
    assert stats.cells_parsed == 2
    assert stats.tasks_emitted == 2


def test_weekly_fallback_uses_default_columns_without_headers() -> None:
    cells = [
        _cell(1, 1, "07.04 - 13.04"),
        _cell(12, 10, "Monday task"),
        _cell(12, 22, "Thursday task"),
        _cell(13, 5, "2026"),
    ]

    rows = _parse_weekly_board_cells(cells)

    assert [row.col_idx for row in rows] == [10, 22]
    assert [row.work_date for row in rows] == [date(2026, 4, 7), date(2026, 4, 10)]


def test_weekly_fallback_returns_empty_for_invalid_week_start_date() -> None:
    cells = [
        _cell(1, 1, "31.02 - 06.03"),
        _cell(11, 10, "Задача"),
        _cell(12, 10, "Task"),
        _cell(13, 5, "2026"),
    ]

    assert _parse_weekly_board_cells(cells) == []


def test_resolve_week_year_falls_back_to_default() -> None:
    cell_map = {(1, 1): _cell(1, 1, "07.04 - 13.04")}
    assert _resolve_week_year(cell_map, 1, default_year=2025) == 2025


def test_detect_task_columns_and_non_task_filtering() -> None:
    cell_map = {
        (11, 9): _cell(11, 9, "Дата"),
        (11, 10): _cell(11, 10, "ЗАДАЧА"),
        (11, 14): _cell(11, 14, "задача 📌"),
    }
    assert _detect_task_columns(cell_map, 11) == [10, 14]

    assert _is_non_task_text("Задача 📌") is True
    assert _is_non_task_text("всего задач: 10") is True
    assert _is_non_task_text("🎯 ЗАДАЧИ на день") is True
    assert _is_non_task_text("real task") is False
