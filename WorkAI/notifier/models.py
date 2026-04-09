"""Notifier dataclasses and level definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NotificationLevel = Literal["infra_critical", "data_warning", "info"]


@dataclass(frozen=True)
class NotificationResult:
    """Result of one notifier delivery attempt."""

    channel: str
    level: NotificationLevel
    subject: str
    delivered: bool
    error: str | None
