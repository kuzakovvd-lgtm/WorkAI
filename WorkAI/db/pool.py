"""Connection pool lifecycle management."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from psycopg import Connection
from psycopg_pool import ConnectionPool

from WorkAI.common import ConfigError, DatabaseError, get_logger
from WorkAI.config import Settings, get_settings

_POOL: ConnectionPool[Connection[Any]] | None = None
_LOG = get_logger(__name__)


def _build_reconnect_failed_callback(
    settings: Settings,
) -> Callable[[ConnectionPool[Connection[Any]]], None]:
    def reconnect_failed(pool: ConnectionPool[Connection[Any]]) -> None:
        _LOG.error(
            "db_pool_reconnect_failed",
            pool_name=pool.name,
            env=settings.app.env,
        )
        if settings.app.env == "prod" and settings.db.exit_on_pool_failure:
            raise SystemExit(2)

    return reconnect_failed


def init_db(settings: Settings | None = None) -> None:
    """Initialize singleton connection pool and fail fast on bad DSN."""

    global _POOL

    if _POOL is not None:
        return

    resolved = settings or get_settings()

    try:
        dsn = resolved.db.require_dsn()
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc

    pool = ConnectionPool(
        conninfo=dsn,
        min_size=resolved.db.min_size,
        max_size=resolved.db.max_size,
        timeout=resolved.db.timeout_sec,
        open=False,
        name="workai",
        reconnect_timeout=60.0,
        reconnect_failed=_build_reconnect_failed_callback(resolved),
        kwargs={"connect_timeout": resolved.db.connect_timeout_sec},
    )

    try:
        pool.open(wait=True, timeout=resolved.db.timeout_sec)
    except Exception as exc:
        pool.close()
        raise DatabaseError("Failed to initialize PostgreSQL connection pool") from exc

    _POOL = pool
    _LOG.info("db_pool_initialized", min_size=resolved.db.min_size, max_size=resolved.db.max_size)


def get_pool() -> ConnectionPool[Connection[Any]]:
    """Return initialized pool or raise."""

    if _POOL is None:
        raise DatabaseError("Database pool is not initialized. Call init_db() first.")
    return _POOL


def close_db() -> None:
    """Close pool if open. Safe to call multiple times."""

    global _POOL

    if _POOL is None:
        return

    _POOL.close()
    _POOL = None


@contextmanager
def connection() -> Iterator[Connection[Any]]:
    """Yield pooled connection."""

    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def apply_lock_timeout(conn: Connection[Any], ms: int) -> None:
    """Set session lock_timeout for admin/migration operations."""

    if ms <= 0:
        raise ValueError("lock timeout must be positive milliseconds")

    with conn.cursor() as cur:
        cur.execute("SET lock_timeout = %s", (f"{ms}ms",))
