from __future__ import annotations

import os
from dataclasses import dataclass

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.notifier import TelegramNotifier


@dataclass
class _SuccessTransport:
    def send_message(self, *, bot_token: str, chat_id: str, text: str, timeout_sec: float) -> None:
        assert bot_token == "token"
        assert chat_id != ""
        assert text != ""
        assert timeout_sec > 0


@dataclass
class _FailTransport:
    def send_message(self, *, bot_token: str, chat_id: str, text: str, timeout_sec: float) -> None:
        raise RuntimeError("telegram offline")


@pytest.mark.integration
def test_notifier_smoke_success_and_failure_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "100")
    monkeypatch.setenv("TELEGRAM_MGMT_CHAT_ID", "200")
    monkeypatch.setenv("WORKAI_NOTIFIER__REQUEST_TIMEOUT_SEC", "5")
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    with connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM notification_log")
        conn.commit()

    success_notifier = TelegramNotifier(transport=_SuccessTransport())
    success_result = success_notifier.send_alert("info", "Smoke success", "body")
    assert success_result.delivered is True

    fail_notifier = TelegramNotifier(transport=_FailTransport())
    fail_result = fail_notifier.send_alert("data_warning", "Smoke failure", None)
    assert fail_result.delivered is False
    assert fail_result.error is not None

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT delivered, error FROM notification_log ORDER BY id"
        )
        rows = cur.fetchall()

    assert len(rows) == 2
    assert bool(rows[0][0]) is True
    assert rows[0][1] is None
    assert bool(rows[1][0]) is False
    assert isinstance(rows[1][1], str)

    close_db()
