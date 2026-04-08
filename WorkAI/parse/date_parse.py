"""Date parsing helpers for parse layer."""

from __future__ import annotations

from datetime import date, datetime


def parse_work_date(text: str, formats: list[str]) -> date | None:
    """Parse a date value using strict format list."""

    value = text.strip()
    if value == "":
        return None

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None
