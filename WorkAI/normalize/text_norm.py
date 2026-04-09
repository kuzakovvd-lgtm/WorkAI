"""Text normalization utilities."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_DASHES_RE = re.compile("[\u2013\u2014\u2212]")


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs to one space and trim."""

    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_unicode(text: str) -> str:
    """Normalize unicode to canonical compatibility form."""

    return unicodedata.normalize("NFKC", text)


def normalize_task_text(text: str) -> str:
    """Apply deterministic task text normalization."""

    normalized = normalize_unicode(text)
    normalized = _DASHES_RE.sub("-", normalized)
    normalized = normalize_whitespace(normalized)
    return normalized
