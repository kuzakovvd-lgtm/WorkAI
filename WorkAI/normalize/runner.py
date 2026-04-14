"""Normalize runner: raw_tasks -> tasks_normalized."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date
from time import perf_counter
from typing import Any
from uuid import uuid4

from psycopg import Cursor

from WorkAI.common import ConfigError, configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import (
    PipelineErrorRecord,
    close_db,
    connection,
    init_db,
    insert_pipeline_error,
    make_payload_excerpt,
)
from WorkAI.normalize.categorizer import CategoryRules, categorize, load_category_rules
from WorkAI.normalize.employee_map import build_employee_alias_map, resolve_employee
from WorkAI.normalize.models import NormalizedTaskRow, NormalizeStats, RawTask
from WorkAI.normalize.queries import (
    delete_tasks_normalized_for_sheet_date,
    fetch_raw_tasks,
    get_or_create_employee_id,
    insert_tasks_normalized_batch,
)
from WorkAI.normalize.text_norm import normalize_task_text
from WorkAI.normalize.time_parse import TimeInfo, extract_time_info

_LOG = get_logger(__name__)
_PENDING_RESULT_MARKERS = (
    "ожид",
    " wait",
    "wip",
    "в работе",
    "todo",
    "to do",
    "вернуться",
)


@dataclass(frozen=True)
class _SheetDateResult:
    rows: list[NormalizedTaskRow]
    stats: NormalizeStats
    errors: list[PipelineErrorRecord]
    limit_exceeded: bool


def run_normalize(settings: Settings | None = None) -> None:
    """Run normalize process for configured spreadsheet source."""

    resolved = settings or get_settings()
    configure_logging(resolved)

    if not resolved.normalize.enabled:
        _LOG.info("normalize_disabled", reason="WORKAI_NORMALIZE__ENABLED is false")
        return

    spreadsheet_id = (resolved.gsheets.spreadsheet_id or "").strip()
    if spreadsheet_id == "":
        raise ConfigError(
            "Normalize requires WORKAI_GSHEETS__SPREADSHEET_ID to identify source spreadsheet"
        )

    # TODO(TZ §4.1): align source selection with full product specification.
    run_id = str(uuid4())
    init_db(resolved)

    alias_map: dict[str, str] = {}
    if resolved.normalize.employee_aliases_file:
        alias_map = build_employee_alias_map(resolved.normalize.employee_aliases_file)

    category_rules: CategoryRules = {}
    if resolved.normalize.category_rules_file:
        category_rules = load_category_rules(resolved.normalize.category_rules_file)

    try:
        with connection() as conn, conn.cursor() as cur:
            all_rows = fetch_raw_tasks(cur, spreadsheet_id)

        by_sheet: dict[str, list[RawTask]] = defaultdict(list)
        for row in all_rows:
            by_sheet[row.sheet_title].append(row)

        for sheet_title, sheet_rows in sorted(by_sheet.items()):
            if len(sheet_rows) > resolved.normalize.max_rows_per_sheet:
                _LOG.warning(
                    "normalize_sheet_too_large",
                    run_id=run_id,
                    spreadsheet_id=spreadsheet_id,
                    sheet_title=sheet_title,
                    raw_rows=len(sheet_rows),
                    max_rows_per_sheet=resolved.normalize.max_rows_per_sheet,
                )
                continue

            by_date: dict[date, list[RawTask]] = defaultdict(list)
            for row in sheet_rows:
                if row.work_date is not None:
                    by_date[row.work_date].append(row)

            for work_date, sheet_date_rows in sorted(by_date.items()):
                started = perf_counter()
                _LOG.info(
                    "normalize_sheet_started",
                    run_id=run_id,
                    spreadsheet_id=spreadsheet_id,
                    sheet_title=sheet_title,
                    work_date=work_date.isoformat(),
                    raw_rows=len(sheet_date_rows),
                )

                result = _normalize_sheet_rows(
                    run_id=run_id,
                    raw_rows=sheet_date_rows,
                    settings=resolved,
                    alias_map=alias_map,
                    category_rules=category_rules,
                )

                if result.errors:
                    for error_record in result.errors:
                        insert_pipeline_error(error_record)

                if result.limit_exceeded:
                    raise RuntimeError(
                        "Normalize error limit exceeded for "
                        f"sheet={sheet_title} work_date={work_date.isoformat()} "
                        f"(max={resolved.normalize.max_errors_per_sheet})"
                    )

                lock_key = _lock_key(
                    sheet_id=f"{spreadsheet_id}:{sheet_title}",
                    work_date=work_date,
                )
                with connection() as conn, conn.cursor() as cur:
                    if not _try_advisory_lock(cur, lock_key):
                        _LOG.warning(
                            "normalize_lock_not_acquired",
                            run_id=run_id,
                            spreadsheet_id=spreadsheet_id,
                            sheet_title=sheet_title,
                            work_date=work_date.isoformat(),
                            lock_key=lock_key,
                        )
                        conn.commit()
                        continue

                    try:
                        employee_ids: dict[str, int] = {}
                        for employee_name_norm in sorted(
                            {row.employee_name_norm for row in result.rows}
                        ):
                            employee_ids[employee_name_norm] = get_or_create_employee_id(
                                cur, employee_name_norm
                            )

                        rows_to_insert = [
                            _with_employee_id(row, employee_ids[row.employee_name_norm])
                            for row in result.rows
                        ]

                        delete_tasks_normalized_for_sheet_date(
                            cur,
                            spreadsheet_id,
                            sheet_title,
                            work_date,
                        )
                        for batch in _chunked(rows_to_insert, 1000):
                            insert_tasks_normalized_batch(cur, batch)
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise
                    finally:
                        _release_advisory_lock(cur, lock_key)

                duration_ms = round((perf_counter() - started) * 1000, 2)
                _LOG.info(
                    "normalize_sheet_written",
                    run_id=run_id,
                    spreadsheet_id=spreadsheet_id,
                    sheet_title=sheet_title,
                    work_date=work_date.isoformat(),
                    rows_emitted=result.stats.rows_emitted,
                    rows_skipped=result.stats.rows_skipped,
                    rows_failed=result.stats.rows_failed,
                    alias_matches=result.stats.alias_matches,
                    fuzzy_matches=result.stats.fuzzy_matches,
                    duration_extracted=result.stats.duration_extracted_count,
                    categories_assigned=result.stats.category_assigned_count,
                    duration_ms=duration_ms,
                )
    finally:
        close_db()


def _normalize_sheet_rows(
    *,
    run_id: str,
    raw_rows: list[RawTask],
    settings: Settings,
    alias_map: dict[str, str],
    category_rules: CategoryRules,
) -> _SheetDateResult:
    stats = NormalizeStats()
    stats.sheets_processed = 1
    stats.raw_rows_read = len(raw_rows)
    rows: list[NormalizedTaskRow] = []
    errors: list[PipelineErrorRecord] = []
    limit_exceeded = False

    for raw in raw_rows:
        employee_raw = (raw.employee_name_raw or "").strip()
        if raw.work_date is None or employee_raw == "":
            stats.rows_skipped += 1
            continue

        try:
            employee_name_norm, employee_method = resolve_employee(
                employee_raw,
                alias_map,
                fuzzy_enabled=settings.normalize.fuzzy_enabled,
                fuzzy_threshold=settings.normalize.fuzzy_threshold,
            )
            if employee_method == "alias":
                stats.alias_matches += 1
            elif employee_method == "fuzzy":
                stats.fuzzy_matches += 1

            if settings.normalize.time_parse_enabled:
                time_info, cleaned_text = extract_time_info(raw.line_text)
            else:
                time_info = None
                cleaned_text = normalize_task_text(raw.line_text)

            if time_info is not None and time_info.duration_minutes is not None:
                stats.duration_extracted_count += 1

            category_code = None
            if category_rules:
                category_code = categorize(cleaned_text, category_rules)
                if category_code is not None:
                    stats.category_assigned_count += 1
            is_zhdun = _is_zhdun_task(cleaned_text)

            rows.append(
                NormalizedTaskRow(
                    raw_task_id=raw.raw_task_id,
                    task_date=raw.work_date,
                    employee_id=0,
                    spreadsheet_id=raw.spreadsheet_id,
                    sheet_title=raw.sheet_title,
                    row_idx=raw.row_idx,
                    col_idx=raw.col_idx,
                    line_no=raw.line_no,
                    work_date=raw.work_date,
                    employee_name_raw=employee_raw,
                    employee_name_norm=employee_name_norm,
                    employee_match_method=employee_method,
                    task_text_raw=raw.line_text,
                    task_text_norm=cleaned_text,
                    time_start=None if time_info is None else time_info.start,
                    time_end=None if time_info is None else time_info.end,
                    duration_minutes=None if time_info is None else time_info.duration_minutes,
                    time_source="none"
                    if time_info is None or time_info.duration_minutes is None
                    else "logged",
                    is_smart=_is_smart_task(cleaned_text),
                    is_micro=_is_micro_task(
                        None if time_info is None else time_info.duration_minutes
                    ),
                    result_confirmed=_is_result_confirmed(
                        text=cleaned_text,
                        time_info=time_info,
                        is_zhdun=is_zhdun,
                    ),
                    is_zhdun=is_zhdun,
                    category_code=category_code,
                    task_category=category_code,
                    canonical_text=cleaned_text,
                    source_cell_ingested_at=raw.cell_ingested_at,
                )
            )
            stats.rows_emitted += 1
        except Exception as exc:
            stats.rows_failed += 1
            source_ref = _source_ref(raw)
            error_payload = {
                "spreadsheet_id": raw.spreadsheet_id,
                "sheet_title": raw.sheet_title,
                "row_idx": raw.row_idx,
                "col_idx": raw.col_idx,
                "line_no": raw.line_no,
                "line_text": raw.line_text,
            }
            errors.append(
                PipelineErrorRecord(
                    phase="normalize",
                    run_id=run_id,
                    sheet_id=raw.sheet_title,
                    work_date=raw.work_date,
                    source_ref=source_ref,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    payload_excerpt=make_payload_excerpt(error_payload),
                )
            )
            if stats.rows_failed > settings.normalize.max_errors_per_sheet:
                limit_exceeded = True
                break

    return _SheetDateResult(
        rows=rows,
        stats=stats,
        errors=errors,
        limit_exceeded=limit_exceeded,
    )


def _source_ref(raw: RawTask) -> str:
    return f"{raw.spreadsheet_id}:{raw.sheet_title}:{raw.row_idx}:{raw.col_idx}:{raw.line_no}"


def _with_employee_id(row: NormalizedTaskRow, employee_id: int) -> NormalizedTaskRow:
    return NormalizedTaskRow(
        raw_task_id=row.raw_task_id,
        task_date=row.task_date,
        employee_id=employee_id,
        spreadsheet_id=row.spreadsheet_id,
        sheet_title=row.sheet_title,
        row_idx=row.row_idx,
        col_idx=row.col_idx,
        line_no=row.line_no,
        work_date=row.work_date,
        employee_name_raw=row.employee_name_raw,
        employee_name_norm=row.employee_name_norm,
        employee_match_method=row.employee_match_method,
        task_text_raw=row.task_text_raw,
        task_text_norm=row.task_text_norm,
        time_start=row.time_start,
        time_end=row.time_end,
        duration_minutes=row.duration_minutes,
        time_source=row.time_source,
        is_smart=row.is_smart,
        is_micro=row.is_micro,
        result_confirmed=row.result_confirmed,
        is_zhdun=row.is_zhdun,
        category_code=row.category_code,
        task_category=row.task_category,
        canonical_text=row.canonical_text,
        source_cell_ingested_at=row.source_cell_ingested_at,
    )


def _is_micro_task(duration_minutes: int | None) -> bool:
    return duration_minutes is not None and duration_minutes <= 15


def _is_zhdun_task(text: str) -> bool:
    lowered = text.casefold()
    return "wait" in lowered or "ожид" in lowered


def _is_smart_task(text: str) -> bool:
    normalized = text.strip()
    return len(normalized) >= 20


def _is_result_confirmed(*, text: str, time_info: TimeInfo | None, is_zhdun: bool) -> bool:
    if time_info is not None and time_info.duration_minutes is not None:
        return True

    normalized = text.strip()
    if normalized == "":
        return False
    if is_zhdun:
        return False

    lowered = normalized.casefold()
    return not any(marker in lowered for marker in _PENDING_RESULT_MARKERS)


def _lock_key(*, sheet_id: str, work_date: date) -> str:
    return f"normalize|{sheet_id}|{work_date.isoformat()}"


def _try_advisory_lock(cursor: Cursor[tuple[bool]], lock_key: str) -> bool:
    cursor.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (lock_key,))
    row = cursor.fetchone()
    return bool(row is not None and row[0] is True)


def _release_advisory_lock(cursor: Cursor[tuple[Any]], lock_key: str) -> None:
    cursor.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (lock_key,))


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
