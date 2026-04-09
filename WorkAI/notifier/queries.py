"""SQL helpers for notifier module."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from psycopg import Cursor

from WorkAI.notifier.models import NotificationLevel


def insert_notification_log(
    cur: Cursor[object],
    *,
    channel: str,
    level: NotificationLevel,
    subject: str,
    body: str | None,
    delivered: bool,
    error: str | None,
) -> None:
    """Insert one notification attempt into notification_log."""

    cur.execute(
        """
        INSERT INTO notification_log (channel, level, subject, body, delivered, error)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (channel, level, subject, body, delivered, error),
    )


def fetch_recent_notifications(cur: Cursor[object], limit: int = 50) -> list[tuple[Any, ...]]:
    """Return most recent notification attempts."""

    cur.execute(
        """
        SELECT id, sent_at, channel, level, subject, body, delivered, error
        FROM notification_log
        ORDER BY sent_at DESC, id DESC
        LIMIT %s
        """,
        (limit,),
    )
    return cast(list[tuple[Any, ...]], cur.fetchall())


def fetch_failed_notifications(cur: Cursor[object], limit: int = 50) -> list[tuple[Any, ...]]:
    """Return recent failed notification attempts only."""

    cur.execute(
        """
        SELECT id, sent_at, channel, level, subject, body, delivered, error
        FROM notification_log
        WHERE delivered = false
        ORDER BY sent_at DESC, id DESC
        LIMIT %s
        """,
        (limit,),
    )
    return cast(list[tuple[Any, ...]], cur.fetchall())


def row_to_log_payload(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert one notification_log row to a JSON-serializable payload."""

    sent_at = row[1]
    sent_at_iso = sent_at.isoformat() if isinstance(sent_at, datetime) else str(sent_at)
    return {
        "id": int(row[0]),
        "sent_at": sent_at_iso,
        "channel": str(row[2]),
        "level": str(row[3]),
        "subject": str(row[4]),
        "body": None if row[5] is None else str(row[5]),
        "delivered": bool(row[6]),
        "error": None if row[7] is None else str(row[7]),
    }
