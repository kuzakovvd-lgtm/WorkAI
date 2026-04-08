"""Ingest orchestration: Google Sheets ranges -> sheet_cells."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from time import perf_counter

from WorkAI.common import configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.ingest.a1 import cell_to_a1, parse_a1_range
from WorkAI.ingest.models import A1RangeSpec, CellValue, ValueRange
from WorkAI.ingest.sheets_client import GoogleApiSheetsClient, SheetsClient

_LOG = get_logger(__name__)

_DELETE_RANGE_SQL = """
DELETE FROM sheet_cells
 WHERE spreadsheet_id = %s
   AND sheet_title = %s
   AND row_idx BETWEEN %s AND %s
   AND col_idx BETWEEN %s AND %s
"""

_INSERT_CELL_SQL = """
INSERT INTO sheet_cells (
    spreadsheet_id,
    sheet_title,
    row_idx,
    col_idx,
    a1,
    value_text,
    ingested_at
)
VALUES (%s, %s, %s, %s, %s, %s, now())
"""


def flatten_value_range(spreadsheet_id: str, value_range: ValueRange) -> tuple[A1RangeSpec, list[CellValue]]:
    """Flatten ValueRange rows into concrete cell records, skipping empty values."""

    spec = parse_a1_range(value_range.range)
    cells: list[CellValue] = []

    for row_offset, row_values in enumerate(value_range.values):
        row_idx = spec.start_row + row_offset
        for col_offset, raw_value in enumerate(row_values):
            col_idx = spec.start_col + col_offset
            text = "" if raw_value is None else str(raw_value)
            if text.strip() == "":
                continue

            cells.append(
                CellValue(
                    spreadsheet_id=spreadsheet_id,
                    sheet_title=spec.sheet_title,
                    row_idx=row_idx,
                    col_idx=col_idx,
                    a1=cell_to_a1(row_idx, col_idx),
                    value_text=text,
                )
            )

    return spec, cells


def run_ingest(settings: Settings | None = None) -> None:
    """Run ingest process for all configured ranges."""

    resolved = settings or get_settings()
    configure_logging(resolved)

    if not resolved.gsheets.enabled:
        _LOG.info("ingest_disabled", reason="WORKAI_GSHEETS__ENABLED is false")
        return

    # TODO(TZ §2.1): align ingest orchestration semantics with full product spec.
    init_db(resolved)
    client = GoogleApiSheetsClient.from_settings(resolved.gsheets)

    try:
        spreadsheet_id = resolved.gsheets.spreadsheet_id or ""
        for range_batch in _chunked(resolved.gsheets.ranges, resolved.gsheets.batch_ranges):
            value_ranges = client.batch_get_values(
                spreadsheet_id,
                list(range_batch),
                value_render_option=resolved.gsheets.value_render_option,
                date_time_render_option=resolved.gsheets.date_time_render_option,
            )

            for value_range in value_ranges:
                started = perf_counter()
                spec, cells = flatten_value_range(spreadsheet_id, value_range)

                _LOG.info(
                    "ingest_range_started",
                    range=value_range.range,
                    sheet_title=spec.sheet_title,
                    rows=spec.end_row - spec.start_row + 1,
                    cols=spec.end_col - spec.start_col + 1,
                )

                _replace_range_cells(spreadsheet_id, spec, cells)

                duration_ms = round((perf_counter() - started) * 1000, 2)
                _LOG.info(
                    "ingest_range_written",
                    range=value_range.range,
                    sheet_title=spec.sheet_title,
                    inserted_cells=len(cells),
                    deleted_area_cells=(spec.end_row - spec.start_row + 1) * (spec.end_col - spec.start_col + 1),
                    duration_ms=duration_ms,
                )
    finally:
        close_db()


def _replace_range_cells(spreadsheet_id: str, spec: A1RangeSpec, cells: list[CellValue]) -> None:
    with connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _DELETE_RANGE_SQL,
                    (
                        spreadsheet_id,
                        spec.sheet_title,
                        spec.start_row,
                        spec.end_row,
                        spec.start_col,
                        spec.end_col,
                    ),
                )

                for batch in _chunked(cells, 1000):
                    params = [
                        (
                            cell.spreadsheet_id,
                            cell.sheet_title,
                            cell.row_idx,
                            cell.col_idx,
                            cell.a1,
                            cell.value_text,
                        )
                        for cell in batch
                    ]
                    if params:
                        cur.executemany(_INSERT_CELL_SQL, params)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


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


def run_ingest_with_client(client: SheetsClient, settings: Settings) -> None:
    """Internal testing helper for ingest execution with injected client."""

    configure_logging(settings)
    if not settings.gsheets.enabled:
        return

    spreadsheet_id = settings.gsheets.spreadsheet_id or ""
    client.batch_get_values(
        spreadsheet_id,
        settings.gsheets.ranges,
        value_render_option=settings.gsheets.value_render_option,
        date_time_render_option=settings.gsheets.date_time_render_option,
    )
