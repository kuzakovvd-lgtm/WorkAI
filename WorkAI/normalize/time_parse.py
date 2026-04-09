"""Rule-based extraction of time information from task text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import time

from WorkAI.normalize.text_norm import normalize_task_text, normalize_whitespace

_RANGE_RE = re.compile(
    r"(?P<start>\b(?:[01]?\d|2[0-3]):[0-5]\d\b)\s*(?:-|to)\s*"
    r"(?P<end>\b(?:[01]?\d|2[0-3]):[0-5]\d\b)",
    flags=re.IGNORECASE,
)
_DURATION_RE = re.compile(
    r"(?P<hours>\d+)\s*(?:h|hr|hrs|hour|hours|ч)\s*(?P<minutes>\d+)?\s*(?:m|min|mins|minute|minutes|м)?",
    flags=re.IGNORECASE,
)
_MINUTES_ONLY_RE = re.compile(
    r"(?P<minutes>\d+)\s*(?:m|min|mins|minute|minutes|м)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class TimeInfo:
    """Extracted time information."""

    start: time | None
    end: time | None
    duration_minutes: int | None


def _parse_hhmm(value: str) -> time:
    hours_str, minutes_str = value.split(":")
    return time(hour=int(hours_str), minute=int(minutes_str))


def _minutes_from_times(start: time, end: time) -> int | None:
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    if end_minutes < start_minutes:
        return None
    return end_minutes - start_minutes


def extract_time_info(text: str) -> tuple[TimeInfo | None, str]:
    """Extract time interval or duration and return cleaned text."""

    working_text = normalize_task_text(text)

    range_match = _RANGE_RE.search(working_text)
    if range_match is not None:
        start = _parse_hhmm(range_match.group("start"))
        end = _parse_hhmm(range_match.group("end"))
        duration = _minutes_from_times(start, end)
        if duration is not None:
            cleaned = (working_text[: range_match.start()] + " " + working_text[range_match.end() :]).strip()
            return TimeInfo(start=start, end=end, duration_minutes=duration), normalize_task_text(cleaned)
        return None, normalize_task_text(working_text)

    duration_match = _DURATION_RE.search(working_text)
    if duration_match is not None:
        hours = int(duration_match.group("hours"))
        minutes_group = duration_match.group("minutes")
        minutes = int(minutes_group) if minutes_group else 0
        duration = hours * 60 + minutes
        cleaned = (
            working_text[: duration_match.start()] + " " + working_text[duration_match.end() :]
        ).strip()
        return (
            TimeInfo(start=None, end=None, duration_minutes=duration),
            normalize_whitespace(normalize_task_text(cleaned)),
        )

    minutes_match = _MINUTES_ONLY_RE.search(working_text)
    if minutes_match is not None:
        minutes = int(minutes_match.group("minutes"))
        cleaned = (working_text[: minutes_match.start()] + " " + working_text[minutes_match.end() :]).strip()
        return (
            TimeInfo(start=None, end=None, duration_minutes=minutes),
            normalize_whitespace(normalize_task_text(cleaned)),
        )

    return None, normalize_task_text(working_text)
