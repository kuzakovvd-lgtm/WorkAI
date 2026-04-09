"""Alembic environment configuration."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.engine import Connection

config = context.config


def _normalize_sqlalchemy_dsn(dsn: str) -> str:
    """Force SQLAlchemy to use psycopg3 driver for PostgreSQL URLs."""

    if dsn.startswith("postgresql+psycopg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn[len("postgresql://") :]
    return dsn


def _get_required_dsn() -> str:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        raise SystemExit(
            "WORKAI_DB__DSN is required for migrations. "
            "Example: export WORKAI_DB__DSN=postgresql://user:pass@host:5432/dbname"
        )
    return _normalize_sqlalchemy_dsn(dsn)


def _get_lock_timeout_ms() -> int:
    raw = os.getenv("WORKAI_DB__LOCK_TIMEOUT_MS", "2000").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit("WORKAI_DB__LOCK_TIMEOUT_MS must be an integer") from exc

    if value <= 0:
        raise SystemExit("WORKAI_DB__LOCK_TIMEOUT_MS must be positive")
    return value


def run_migrations_offline() -> None:
    """Run migrations without a DB connection."""

    dsn = _get_required_dsn()
    lock_timeout_ms = _get_lock_timeout_ms()

    context.configure(
        url=dsn,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.execute(f"SET lock_timeout = '{lock_timeout_ms}ms'")
        context.run_migrations()


def _run_online_with_connection(connection: Connection) -> None:
    lock_timeout_ms = _get_lock_timeout_ms()
    context.configure(connection=connection, target_metadata=None)

    with context.begin_transaction():
        connection.execute(text(f"SET lock_timeout = '{lock_timeout_ms}ms'"))
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a DB connection."""

    existing_connection = config.attributes.get("connection")
    if isinstance(existing_connection, Connection):
        _run_online_with_connection(existing_connection)
        return

    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _get_required_dsn()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _run_online_with_connection(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
