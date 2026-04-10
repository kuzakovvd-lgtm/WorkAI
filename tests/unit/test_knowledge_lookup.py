from __future__ import annotations

from contextlib import contextmanager

from WorkAI.knowledge_base import lookup
from WorkAI.knowledge_base.models import KnowledgeSearchResult
from WorkAI.knowledge_base.queries import LOOKUP_METHODOLOGY_SQL


class _DummyCursor:
    pass


class _DummyConn:
    @contextmanager
    def cursor(self) -> _DummyCursor:
        yield _DummyCursor()


def test_lookup_sql_uses_postgres_fts() -> None:
    assert "websearch_to_tsquery('russian'" in LOOKUP_METHODOLOGY_SQL
    assert "ts_rank" in LOOKUP_METHODOLOGY_SQL


def test_lookup_cache_hits(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls = {"count": 0}

    def fake_get_settings():
        from WorkAI.config import Settings

        return Settings()

    def fake_init_db(_settings):
        return None

    @contextmanager
    def fake_connection_cm():
        yield _DummyConn()

    def fake_lookup_articles(cursor, query, limit, *, excerpt_chars=240):
        del cursor
        del excerpt_chars
        calls["count"] += 1
        return [
            KnowledgeSearchResult(
                source_path="/tmp/source.md",
                title=f"Result for {query}",
                body_excerpt="text",
                tags=["ghost"],
                rank=float(limit),
            )
        ]

    monkeypatch.setattr(lookup, "get_settings", fake_get_settings)
    monkeypatch.setattr(lookup, "init_db", fake_init_db)
    monkeypatch.setattr(lookup, "connection", fake_connection_cm)
    monkeypatch.setattr(lookup, "lookup_articles", fake_lookup_articles)

    lookup.clear_lookup_cache()

    first = lookup.lookup_methodology("ghost time", limit=5)
    second = lookup.lookup_methodology("ghost time", limit=5)

    assert len(first) == 1
    assert len(second) == 1
    assert calls["count"] == 1

    lookup.clear_lookup_cache()
    third = lookup.lookup_methodology("ghost time", limit=5)
    assert len(third) == 1
    assert calls["count"] == 2
