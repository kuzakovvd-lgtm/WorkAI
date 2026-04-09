"""Telegram notifier transport with mandatory DB attempt logging."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from WorkAI.common import ConfigError, get_logger
from WorkAI.config import NotifierSettings, Settings, get_settings
from WorkAI.db import connection, init_db
from WorkAI.notifier.models import NotificationLevel, NotificationResult
from WorkAI.notifier.queries import insert_notification_log

_LOG = get_logger(__name__)
_INFO_CHANNEL_FALLBACK = "telegram_admin_fallback"


class TelegramTransport(Protocol):
    """Transport abstraction for Telegram API calls."""

    def send_message(self, *, bot_token: str, chat_id: str, text: str, timeout_sec: float) -> None:
        """Send one telegram message or raise on failure."""


@dataclass(frozen=True)
class HttpTelegramTransport:
    """Default HTTP transport using Telegram Bot API."""

    api_base_url: str = "https://api.telegram.org"

    def send_message(self, *, bot_token: str, chat_id: str, text: str, timeout_sec: float) -> None:
        payload = urllib.parse.urlencode(
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")
        url = f"{self.api_base_url}/bot{bot_token}/sendMessage"
        request = urllib.request.Request(url=url, data=payload, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:  # pragma: no cover (covered via mocked transport tests)
            raise RuntimeError(str(exc)) from exc

        parsed = json.loads(body)
        if not bool(parsed.get("ok", False)):
            raise RuntimeError(f"Telegram API rejected message: {body[:500]}")


class TelegramNotifier:
    """Notifier implementation with level routing and DB logging."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        transport: TelegramTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._cfg: NotifierSettings = self._settings.notifier
        self._transport = transport or HttpTelegramTransport()

    def send_alert(
        self,
        level: NotificationLevel,
        subject: str,
        body: str | None = None,
    ) -> NotificationResult:
        """Send one alert attempt and always persist attempt record."""

        if subject.strip() == "":
            raise ValueError("Notification subject must not be empty")

        init_db(self._settings)

        channel, chat_id = self._resolve_target(level)
        bot_token = (self._cfg.telegram_bot_token or "").strip()
        message_text = self._render_message(level, subject, body)

        delivered = False
        error_message: str | None = None

        try:
            if bot_token == "":
                raise ConfigError("TELEGRAM_BOT_TOKEN is not configured")
            if chat_id is None or chat_id.strip() == "":
                raise ConfigError(f"Telegram chat id for level '{level}' is not configured")

            self._transport.send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                text=message_text,
                timeout_sec=self._cfg.request_timeout_sec,
            )
            delivered = True
            _LOG.info(
                "notifier_alert_sent",
                level=level,
                channel=channel,
                subject=subject,
            )
        except Exception as exc:
            error_message = str(exc)
            _LOG.warning(
                "notifier_alert_failed",
                level=level,
                channel=channel,
                subject=subject,
                error_type=type(exc).__name__,
            )
        finally:
            with connection() as conn, conn.cursor() as cur:
                insert_notification_log(
                    cur,
                    channel=channel,
                    level=level,
                    subject=subject,
                    body=body,
                    delivered=delivered,
                    error=error_message,
                )
                conn.commit()

        return NotificationResult(
            channel=channel,
            level=level,
            subject=subject,
            delivered=delivered,
            error=error_message,
        )

    def _resolve_target(self, level: NotificationLevel) -> tuple[str, str | None]:
        if level == "infra_critical":
            return "telegram_admin", self._cfg.telegram_admin_chat_id
        if level == "data_warning":
            return "telegram_mgmt", self._cfg.telegram_mgmt_chat_id
        if level == "info":
            if self._cfg.telegram_info_chat_id and self._cfg.telegram_info_chat_id.strip() != "":
                return "telegram_info", self._cfg.telegram_info_chat_id
            return _INFO_CHANNEL_FALLBACK, self._cfg.telegram_admin_chat_id
        raise ValueError(f"Unsupported notification level: {level}")

    @staticmethod
    def _render_message(level: NotificationLevel, subject: str, body: str | None) -> str:
        prefix = f"[WORKAI:{level}]"
        if body is None or body.strip() == "":
            return f"{prefix} {subject.strip()}"
        return f"{prefix} {subject.strip()}\n\n{body.strip()}"
