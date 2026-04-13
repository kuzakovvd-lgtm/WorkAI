from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest
from WorkAI.config import Settings
from WorkAI.knowledge_base import indexer
from WorkAI.knowledge_base.models import KnowledgeArticleDocument


class _CursorStub:
    def __enter__(self) -> _CursorStub:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class _ConnectionStub:
    def __init__(self) -> None:
        self.commits = 0

    def __enter__(self) -> _ConnectionStub:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def cursor(self) -> _CursorStub:
        return _CursorStub()

    def commit(self) -> None:
        self.commits += 1


def _patch_connection(monkeypatch: pytest.MonkeyPatch, conn: _ConnectionStub) -> None:
    @contextmanager
    def _connection() -> _ConnectionStub:
        yield conn

    monkeypatch.setattr(indexer, "connection", _connection)


def test_index_knowledge_sources_counts_success_and_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "ok.md").write_text("# OK\n\nBody text", encoding="utf-8")
    (tmp_path / "broken.md").write_text("broken", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("ignored", encoding="utf-8")

    calls: dict[str, int] = {"init": 0, "close": 0, "cache_clear": 0}
    conn = _ConnectionStub()
    _patch_connection(monkeypatch, conn)

    monkeypatch.setattr(indexer, "configure_logging", lambda *_: None)
    monkeypatch.setattr(indexer, "SUPPORTED_KNOWLEDGE_EXTENSIONS", {".md"})
    monkeypatch.setattr(indexer, "init_db", lambda *_: calls.__setitem__("init", calls["init"] + 1))
    monkeypatch.setattr(indexer, "close_db", lambda: calls.__setitem__("close", calls["close"] + 1))
    monkeypatch.setattr(
        indexer, "clear_lookup_cache", lambda: calls.__setitem__("cache_clear", calls["cache_clear"] + 1)
    )

    def _parse(path: Path) -> KnowledgeArticleDocument:
        if path.name == "broken.md":
            raise ValueError("bad file")
        return KnowledgeArticleDocument(
            source_path=str(path),
            title="Title",
            body="alpha beta gamma",
            tags=["tag1"],
        )

    monkeypatch.setattr(indexer, "parse_article_document", _parse)
    monkeypatch.setattr(indexer, "chunk_text", lambda body: [body[:5], body[6:10]])
    monkeypatch.setattr(indexer, "upsert_articles_batch", lambda cur, articles: len(articles))
    monkeypatch.setattr(indexer, "replace_article_chunks", lambda cur, source_path, chunks: len(chunks))

    result = indexer.index_knowledge_sources(
        Settings.model_validate({"db": {"dsn": "postgresql://u:p@localhost:5432/workai"}}),
        source_dir=tmp_path,
    )

    assert result.files_seen == 2
    assert result.rows_upserted == 1
    assert result.chunks_upserted == 2
    assert result.errors_count == 1
    assert conn.commits == 1
    assert calls == {"init": 1, "close": 1, "cache_clear": 1}


def test_index_knowledge_sources_handles_missing_source_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _ConnectionStub()
    _patch_connection(monkeypatch, conn)

    monkeypatch.setattr(indexer, "configure_logging", lambda *_: None)
    monkeypatch.setattr(indexer, "init_db", lambda *_: None)
    monkeypatch.setattr(indexer, "close_db", lambda: None)
    monkeypatch.setattr(indexer, "clear_lookup_cache", lambda: None)
    monkeypatch.setattr(indexer, "upsert_articles_batch", lambda cur, articles: len(articles))
    monkeypatch.setattr(indexer, "replace_article_chunks", lambda cur, source_path, chunks: len(chunks))

    result = indexer.index_knowledge_sources(
        Settings.model_validate({"db": {"dsn": "postgresql://u:p@localhost:5432/workai"}}),
        source_dir=Path("/definitely/not/existing/path"),
    )

    assert result.files_seen == 0
    assert result.rows_upserted == 0
    assert result.chunks_upserted == 0
    assert result.errors_count == 0
    assert conn.commits == 1
