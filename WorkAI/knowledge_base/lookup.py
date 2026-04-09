"""Knowledge base lookup with PostgreSQL FTS and LRU cache."""

from __future__ import annotations

from functools import lru_cache

from WorkAI.common import configure_logging, get_logger
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.knowledge_base.models import KnowledgeSearchResult
from WorkAI.knowledge_base.queries import lookup_articles

_LOG = get_logger(__name__)


@lru_cache(maxsize=100)
def _lookup_cached(query: str, limit: int) -> tuple[KnowledgeSearchResult, ...]:
    resolved = get_settings()
    init_db(resolved)
    try:
        with connection() as conn, conn.cursor() as cur:
            rows = lookup_articles(cur, query=query, limit=limit)
    finally:
        close_db()
    return tuple(rows)


def lookup_methodology(query: str, limit: int = 5) -> list[KnowledgeSearchResult]:
    """Lookup methodology documents by FTS query with cache key (query, limit)."""

    resolved = get_settings()
    configure_logging(resolved)

    cleaned_query = query.strip()
    if cleaned_query == "":
        return []

    bounded_limit = max(1, min(limit, 100))
    results = list(_lookup_cached(cleaned_query, bounded_limit))

    _LOG.info(
        "knowledge_lookup_completed",
        query=cleaned_query,
        limit=bounded_limit,
        results=len(results),
        cache_size=100,
    )
    return results


def clear_lookup_cache() -> None:
    """Clear lookup cache, e.g. after index refresh."""

    _lookup_cached.cache_clear()
