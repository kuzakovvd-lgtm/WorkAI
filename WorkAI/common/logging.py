"""Structlog configuration helpers."""

from __future__ import annotations

import logging
from typing import Any

import structlog
from structlog.typing import EventDict, Processor

from WorkAI.config import Settings

_LOGGING_SIGNATURE: tuple[str, bool, str, str, str] | None = None


def configure_logging(settings: Settings) -> None:
    """Configure process logging in an idempotent way."""

    global _LOGGING_SIGNATURE

    signature = (
        settings.app.env,
        settings.log.json_output,
        settings.log.level,
        settings.app.service_name,
        settings.app.version,
    )
    if signature == _LOGGING_SIGNATURE:
        return

    log_level = getattr(logging, settings.log.level)
    logging.basicConfig(level=log_level, format="%(message)s", force=True)

    def add_defaults(_: Any, __: str, event_dict: EventDict) -> EventDict:
        event_dict.setdefault("service", settings.app.service_name)
        event_dict.setdefault("env", settings.app.env)
        event_dict.setdefault("version", settings.app.version)
        return event_dict

    renderer: Processor
    if settings.app.env == "prod" or settings.log.json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_defaults,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _LOGGING_SIGNATURE = signature


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a typed structlog logger."""

    return structlog.stdlib.get_logger(name)
