from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from WorkAI.config import get_settings
from WorkAI.notifier import TelegramNotifier


@dataclass
class _FakeTransport:
    should_fail: bool = False

    def send_message(self, *, bot_token: str, chat_id: str, text: str, timeout_sec: float) -> None:
        assert bot_token == "token"
        assert chat_id != ""
        assert text != ""
        assert timeout_sec > 0
        if self.should_fail:
            raise RuntimeError("transport failed")


class _FakeCursor:
    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class _FakeConn:
    def __init__(self) -> None:
        self.commits = 0

    def cursor(self) -> _FakeCursor:
        return _FakeCursor()

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


@pytest.fixture
def notifier_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "100")
    monkeypatch.setenv("TELEGRAM_MGMT_CHAT_ID", "200")
    monkeypatch.setenv("TELEGRAM_INFO_CHAT_ID", "300")
    get_settings.cache_clear()


def test_notifier_success_and_log_call(monkeypatch: pytest.MonkeyPatch, notifier_env: None) -> None:
    from WorkAI.notifier import telegram_bot as module

    fake_conn = _FakeConn()
    captured: dict[str, Any] = {}

    monkeypatch.setattr(module, "init_db", lambda settings: None)
    monkeypatch.setattr(module, "connection", lambda: fake_conn)

    def _capture_insert(cur: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(module, "insert_notification_log", _capture_insert)

    notifier = TelegramNotifier(transport=_FakeTransport())
    result = notifier.send_alert(level="infra_critical", subject="CPU spike", body="host=prod-1")

    assert result.delivered is True
    assert result.error is None
    assert captured["channel"] == "telegram_admin"
    assert captured["level"] == "infra_critical"
    assert captured["delivered"] is True
    assert fake_conn.commits == 1


def test_notifier_failure_and_log_call(monkeypatch: pytest.MonkeyPatch, notifier_env: None) -> None:
    from WorkAI.notifier import telegram_bot as module

    fake_conn = _FakeConn()
    captured: dict[str, Any] = {}

    monkeypatch.setattr(module, "init_db", lambda settings: None)
    monkeypatch.setattr(module, "connection", lambda: fake_conn)

    def _capture_insert(cur: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(module, "insert_notification_log", _capture_insert)

    notifier = TelegramNotifier(transport=_FakeTransport(should_fail=True))
    result = notifier.send_alert(level="data_warning", subject="Data gap", body=None)

    assert result.delivered is False
    assert isinstance(result.error, str)
    assert captured["channel"] == "telegram_mgmt"
    assert captured["level"] == "data_warning"
    assert captured["delivered"] is False
    assert isinstance(captured["error"], str)
    assert fake_conn.commits == 1


def test_notifier_info_fallback_to_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    from WorkAI.notifier import telegram_bot as module

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "100")
    monkeypatch.setenv("TELEGRAM_MGMT_CHAT_ID", "200")
    monkeypatch.delenv("TELEGRAM_INFO_CHAT_ID", raising=False)
    get_settings.cache_clear()

    fake_conn = _FakeConn()
    captured: dict[str, Any] = {}

    monkeypatch.setattr(module, "init_db", lambda settings: None)
    monkeypatch.setattr(module, "connection", lambda: fake_conn)

    def _capture_insert(cur: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(module, "insert_notification_log", _capture_insert)

    notifier = TelegramNotifier(transport=_FakeTransport())
    result = notifier.send_alert(level="info", subject="FYI", body=None)

    assert result.delivered is True
    assert captured["channel"] == "telegram_admin_fallback"
