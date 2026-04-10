"""Knowledge base models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeArticleDocument:
    """Parsed article payload ready for DB indexing."""

    source_path: str
    title: str
    body: str
    tags: list[str]


@dataclass(frozen=True)
class KnowledgeSearchResult:
    """Lookup result returned by methodology search."""

    source_path: str
    title: str
    body_excerpt: str
    tags: list[str]
    rank: float


@dataclass(frozen=True)
class KnowledgeIndexResult:
    """Summary for one knowledge indexing run."""

    files_seen: int
    rows_upserted: int
    chunks_upserted: int
    errors_count: int
