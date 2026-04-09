"""Small DB query helpers based on the shared pool."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from time import perf_counter
from typing import Any

from WorkAI.common import get_logger
from WorkAI.db.pool import connection

QueryParams = Mapping[str, Any] | Sequence[Any] | None
Row = tuple[Any, ...]
_LOG = get_logger(__name__)
_PIPELINE_ERROR_MESSAGE_LIMIT = 4096
_PIPELINE_PAYLOAD_LIMIT = 4096


@dataclass(frozen=True)
class PipelineErrorRecord:
    """Record-level failure details for DLQ table."""

    phase: str
    run_id: str
    sheet_id: str | None
    work_date: date | None
    source_ref: str
    error_type: str
    error_message: str
    payload_excerpt: str | None


INSERT_PIPELINE_ERROR_SQL = """
INSERT INTO pipeline_errors (
    phase,
    run_id,
    sheet_id,
    work_date,
    source_ref,
    error_type,
    error_message,
    payload_excerpt,
    error_hash,
    created_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT ON CONSTRAINT uq_pipeline_errors_phase_source_hash
DO UPDATE SET
    run_id = EXCLUDED.run_id,
    sheet_id = EXCLUDED.sheet_id,
    work_date = EXCLUDED.work_date,
    error_type = EXCLUDED.error_type,
    error_message = EXCLUDED.error_message,
    payload_excerpt = EXCLUDED.payload_excerpt,
    created_at = now()
"""


def _compact_sql(sql: str) -> str:
    return " ".join(sql.split())[:200]


def execute(sql: str, params: QueryParams = None) -> None:
    """Execute statement and commit transaction."""

    started = perf_counter()
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    _LOG.debug("sql_execute", duration_ms=round((perf_counter() - started) * 1000, 2), sql=_compact_sql(sql))


def fetch_one(sql: str, params: QueryParams = None) -> Row | None:
    """Execute query and fetch one row."""

    started = perf_counter()
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    _LOG.debug("sql_fetch_one", duration_ms=round((perf_counter() - started) * 1000, 2), sql=_compact_sql(sql))
    if row is None:
        return None
    return tuple(row)


def fetch_all(sql: str, params: QueryParams = None) -> list[Row]:
    """Execute query and fetch all rows."""

    started = perf_counter()
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    _LOG.debug("sql_fetch_all", duration_ms=round((perf_counter() - started) * 1000, 2), sql=_compact_sql(sql))
    return [tuple(row) for row in rows]


def insert_pipeline_error(record: PipelineErrorRecord) -> None:
    """Persist one pipeline error record with deterministic hash deduplication."""

    message = record.error_message.strip()[:_PIPELINE_ERROR_MESSAGE_LIMIT]
    payload = None if record.payload_excerpt is None else record.payload_excerpt.strip()[:_PIPELINE_PAYLOAD_LIMIT]
    hash_source = f"{record.phase}|{record.source_ref}|{record.error_type}|{message}"
    error_hash = hashlib.sha256(hash_source.encode("utf-8")).hexdigest()

    started = perf_counter()
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                INSERT_PIPELINE_ERROR_SQL,
                (
                    record.phase,
                    record.run_id,
                    record.sheet_id,
                    record.work_date,
                    record.source_ref,
                    record.error_type,
                    message,
                    payload,
                    error_hash,
                ),
            )
        conn.commit()

    _LOG.debug(
        "sql_insert_pipeline_error",
        duration_ms=round((perf_counter() - started) * 1000, 2),
        phase=record.phase,
        source_ref=record.source_ref,
    )


def make_payload_excerpt(payload: Mapping[str, Any] | None) -> str | None:
    """Serialize payload excerpt safely to bounded JSON text."""

    if payload is None:
        return None
    try:
        rendered = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    except TypeError:
        rendered = json.dumps({"repr": repr(payload)}, ensure_ascii=True, sort_keys=True)
    return rendered[:_PIPELINE_PAYLOAD_LIMIT]
