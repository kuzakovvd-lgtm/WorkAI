"""Deterministic text chunking for large knowledge sources."""

from __future__ import annotations

import re

WHITESPACE_RE = re.compile(r"\s+")


def chunk_text(text: str, *, max_chars: int = 3000, overlap: int = 300) -> list[str]:
    """Split text into stable overlapping chunks for FTS indexing."""

    normalized = WHITESPACE_RE.sub(" ", text).strip()
    if normalized == "":
        return []

    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= max_chars:
        raise ValueError("overlap must be < max_chars")

    parts: list[str] = []
    start = 0
    size = len(normalized)

    while start < size:
        end = min(start + max_chars, size)
        if end < size:
            split_at = normalized.rfind(" ", start, end)
            if split_at > start:
                end = split_at

        piece = normalized[start:end].strip()
        if piece != "":
            parts.append(piece)

        if end >= size:
            break

        next_start = max(0, end - overlap)
        if next_start <= start:
            next_start = end
        start = next_start

    return parts

