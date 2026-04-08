"""Database introspection helpers."""

from __future__ import annotations

from typing import Any

from psycopg import Connection

from WorkAI.common import DatabaseError


def get_db_version(conn: Connection[Any]) -> str:
    """Return PostgreSQL server version string."""

    with conn.cursor() as cur:
        cur.execute("SELECT version()")
        row = cur.fetchone()

    if row is None:
        raise DatabaseError("SELECT version() returned no rows")

    return str(row[0])


def get_alembic_version(conn: Connection[Any]) -> str | None:
    """Return current Alembic version or None if table does not exist."""

    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.alembic_version')")
        table_name = cur.fetchone()
        if table_name is None or table_name[0] is None:
            return None

        cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
        version_row = cur.fetchone()

    if version_row is None:
        return None

    return str(version_row[0])
