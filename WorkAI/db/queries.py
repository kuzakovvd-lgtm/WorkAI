"""Small DB query helpers based on the shared pool."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any

from WorkAI.common import get_logger
from WorkAI.db.pool import connection

QueryParams = Mapping[str, Any] | Sequence[Any] | None
Row = tuple[Any, ...]
_LOG = get_logger(__name__)


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
