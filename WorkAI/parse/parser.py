"""Deterministic parse function for sheet_cells -> raw_tasks rows."""

from __future__ import annotations

import re
from datetime import date, timedelta

from WorkAI.config import ParseSettings
from WorkAI.parse.layout import build_date_by_col, build_employee_by_row
from WorkAI.parse.models import ParseStats, RawTaskRow, SheetCell

_WEEK_RANGE_RE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\s*$")
_YEAR_RE = re.compile(r"^\s*(20\d{2})\s*$")


def parse_cells(cells: list[SheetCell], settings: ParseSettings) -> tuple[list[RawTaskRow], ParseStats]:
    """Parse a sheet cell collection into raw task rows."""

    stats = ParseStats(sheets_processed=1 if cells else 0, cells_read=len(cells))
    if not cells:
        return [], stats

    date_by_col = build_date_by_col(
        cells,
        header_row_idx=settings.header_row_idx,
        employee_col_idx=settings.employee_col_idx,
        formats=settings.date_formats,
    )
    employee_by_row = build_employee_by_row(
        cells,
        header_row_idx=settings.header_row_idx,
        employee_col_idx=settings.employee_col_idx,
    )

    result: list[RawTaskRow] = []

    # deterministic order to keep repeated runs stable
    for cell in sorted(cells, key=lambda item: (item.row_idx, item.col_idx)):
        if cell.row_idx <= settings.header_row_idx:
            continue
        if cell.col_idx <= settings.employee_col_idx:
            continue

        value = "" if cell.value_text is None else cell.value_text
        if value.strip() == "":
            continue

        employee_name = employee_by_row.get(cell.row_idx)
        if employee_name is None:
            stats.cells_skipped_missing_employee += 1
            continue

        work_date = date_by_col.get(cell.col_idx)
        if work_date is None:
            stats.cells_skipped_missing_date += 1
            continue

        stats.cells_parsed += 1

        try:
            lines = [line.strip() for line in value.splitlines() if line.strip()]
            for line_no, line_text in enumerate(lines, start=1):
                result.append(
                    RawTaskRow(
                        spreadsheet_id=cell.spreadsheet_id,
                        sheet_title=cell.sheet_title,
                        row_idx=cell.row_idx,
                        col_idx=cell.col_idx,
                        cell_a1=cell.a1,
                        cell_ingested_at=cell.ingested_at,
                        employee_name_raw=employee_name,
                        work_date=work_date,
                        line_no=line_no,
                        line_text=line_text,
                    )
                )
        except Exception:
            stats.cells_failed += 1

    if result:
        stats.tasks_emitted = len(result)
        return result, stats

    # Fallback for weekly board sheets:
    # tasks are grouped by weekdays in fixed column blocks, employee is sheet title.
    fallback_rows = _parse_weekly_board_cells(cells)
    if fallback_rows:
        stats.cells_parsed = len(fallback_rows)
        stats.tasks_emitted = len(fallback_rows)
        # Missing-date/employee skips in strict mode are not actionable once fallback succeeded.
        stats.cells_skipped_missing_date = 0
        stats.cells_skipped_missing_employee = 0
        return fallback_rows, stats

    stats.tasks_emitted = 0
    return [], stats


def _parse_weekly_board_cells(cells: list[SheetCell]) -> list[RawTaskRow]:
    if not cells:
        return []

    cell_map: dict[tuple[int, int], SheetCell] = {(cell.row_idx, cell.col_idx): cell for cell in cells}
    first_cell = cells[0]
    employee_name = first_cell.sheet_title.strip()

    block_starts = sorted(
        {
            cell.row_idx
            for cell in cells
            if cell.col_idx == 1
            and cell.value_text is not None
            and _WEEK_RANGE_RE.match(cell.value_text.strip()) is not None
        }
    )
    if not block_starts:
        return []

    max_row = max(cell.row_idx for cell in cells)
    out: list[RawTaskRow] = []

    for idx, block_start in enumerate(block_starts):
        block_end = block_starts[idx + 1] - 1 if idx + 1 < len(block_starts) else max_row
        week_cell = cell_map.get((block_start, 1))
        if week_cell is None or week_cell.value_text is None:
            continue
        week_match = _WEEK_RANGE_RE.match(week_cell.value_text.strip())
        if week_match is None:
            continue

        start_day = int(week_match.group(1))
        start_month = int(week_match.group(2))
        year = _resolve_week_year(cell_map, block_start, default_year=week_cell.ingested_at.year)
        try:
            monday_date = date(year, start_month, start_day)
        except ValueError:
            continue

        header_row = block_start + 10
        task_columns = _detect_task_columns(cell_map, header_row)
        if not task_columns:
            task_columns = [10, 14, 18, 22, 26]

        # Data rows: immediately after header, until next block start.
        for row_idx in range(header_row + 1, block_end + 1):
            for day_offset, task_col in enumerate(task_columns):
                task_cell = cell_map.get((row_idx, task_col))
                if task_cell is None or task_cell.value_text is None:
                    continue
                text = task_cell.value_text.strip()
                if text == "" or _is_non_task_text(text):
                    continue

                work_date = monday_date + timedelta(days=day_offset)
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if not lines:
                    continue

                for line_no, line_text in enumerate(lines, start=1):
                    out.append(
                        RawTaskRow(
                            spreadsheet_id=task_cell.spreadsheet_id,
                            sheet_title=task_cell.sheet_title,
                            row_idx=task_cell.row_idx,
                            col_idx=task_cell.col_idx,
                            cell_a1=task_cell.a1,
                            cell_ingested_at=task_cell.ingested_at,
                            employee_name_raw=employee_name if employee_name else None,
                            work_date=work_date,
                            line_no=line_no,
                            line_text=line_text,
                        )
                    )

    out.sort(key=lambda row: (row.sheet_title, row.row_idx, row.col_idx, row.line_no))
    return out


def _resolve_week_year(
    cell_map: dict[tuple[int, int], SheetCell],
    block_start: int,
    *,
    default_year: int,
) -> int:
    # In real sheets the year is located near the weekly header block.
    candidates = [
        cell_map.get((block_start + 12, 5)),
        cell_map.get((block_start + 44, 5)),
    ]
    for cell in candidates:
        if cell is None or cell.value_text is None:
            continue
        match = _YEAR_RE.match(cell.value_text.strip())
        if match is not None:
            return int(match.group(1))
    return default_year


def _detect_task_columns(cell_map: dict[tuple[int, int], SheetCell], header_row: int) -> list[int]:
    columns: list[int] = []
    for (row_idx, col_idx), cell in cell_map.items():
        if row_idx != header_row or cell.value_text is None:
            continue
        if "задача" in cell.value_text.casefold():
            columns.append(col_idx)
    return sorted(set(columns))


def _is_non_task_text(value: str) -> bool:
    normalized = value.casefold()
    if normalized in {"задача 📌", "дата", "заметки 📝"}:
        return True
    if normalized in {"true", "false"}:
        return True
    if normalized.startswith("всего задач") or normalized.startswith("готово"):
        return True
    if normalized.startswith("в работе") or normalized.startswith("нужна помощь"):
        return True
    if normalized.startswith("нет статуса") or normalized.startswith("отменено"):
        return True
    return bool(normalized.startswith("🎯 задачи"))
