"""Parse runner: sheet_cells -> raw_tasks."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from time import perf_counter

from WorkAI.common import ConfigError, configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.parse.models import SheetCell
from WorkAI.parse.parser import parse_cells
from WorkAI.parse.queries import (
    delete_raw_tasks_for_sheet,
    fetch_sheet_cells,
    insert_raw_tasks_batch,
)

_LOG = get_logger(__name__)


def run_parse(settings: Settings | None = None) -> None:
    """Run parse process for configured spreadsheet source."""

    resolved = settings or get_settings()
    configure_logging(resolved)

    if not resolved.parse.enabled:
        _LOG.info("parse_disabled", reason="WORKAI_PARSE__ENABLED is false")
        return

    spreadsheet_id = (resolved.gsheets.spreadsheet_id or "").strip()
    if spreadsheet_id == "":
        raise ConfigError(
            "Parse requires WORKAI_GSHEETS__SPREADSHEET_ID to identify source spreadsheet"
        )

    # TODO(TZ §3.1): align parse source selection with full product specification.
    init_db(resolved)

    try:
        with connection() as conn, conn.cursor() as cur:
            all_cells = fetch_sheet_cells(cur, spreadsheet_id)

        by_sheet: dict[str, list[SheetCell]] = defaultdict(list)
        for cell in all_cells:
            by_sheet[cell.sheet_title].append(cell)

        for sheet_title, sheet_cells in sorted(by_sheet.items()):
            if len(sheet_cells) > resolved.parse.max_cells_per_sheet:
                _LOG.warning(
                    "parse_sheet_too_large",
                    spreadsheet_id=spreadsheet_id,
                    sheet_title=sheet_title,
                    cells=len(sheet_cells),
                    max_cells_per_sheet=resolved.parse.max_cells_per_sheet,
                )
                continue

            started = perf_counter()
            _LOG.info(
                "parse_sheet_started",
                spreadsheet_id=spreadsheet_id,
                sheet_title=sheet_title,
                cells=len(sheet_cells),
            )

            rows, stats = parse_cells(sheet_cells, resolved.parse)

            with connection() as conn:
                try:
                    with conn.cursor() as cur:
                        delete_raw_tasks_for_sheet(cur, spreadsheet_id, sheet_title)
                        for batch in _chunked(rows, 1000):
                            insert_raw_tasks_batch(cur, batch)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

            employee_count = len({r.employee_name_raw for r in rows if r.employee_name_raw})
            date_count = len({r.work_date for r in rows if r.work_date is not None})
            duration_ms = round((perf_counter() - started) * 1000, 2)

            _LOG.info(
                "parse_sheet_written",
                spreadsheet_id=spreadsheet_id,
                sheet_title=sheet_title,
                tasks_emitted=stats.tasks_emitted,
                employees_detected=employee_count,
                dates_detected=date_count,
                cells_skipped_missing_date=stats.cells_skipped_missing_date,
                cells_skipped_missing_employee=stats.cells_skipped_missing_employee,
                cells_failed=stats.cells_failed,
                duration_ms=duration_ms,
            )
    finally:
        close_db()


def _chunked[T](items: Iterable[T], size: int) -> Iterator[list[T]]:
    if size <= 0:
        raise ValueError("Chunk size must be positive")

    batch: list[T] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
