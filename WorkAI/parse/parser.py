"""Deterministic parse function for sheet_cells -> raw_tasks rows."""

from __future__ import annotations

from WorkAI.config import ParseSettings
from WorkAI.parse.layout import build_date_by_col, build_employee_by_row
from WorkAI.parse.models import ParseStats, RawTaskRow, SheetCell


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

    stats.tasks_emitted = len(result)
    return result, stats
