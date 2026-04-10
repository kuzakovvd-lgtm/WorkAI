"""Knowledge base indexer for methodology sources."""

from __future__ import annotations

from pathlib import Path

from WorkAI.common import configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.knowledge_base.chunking import chunk_text
from WorkAI.knowledge_base.extractors import (
    SUPPORTED_KNOWLEDGE_EXTENSIONS,
    parse_article_document,
)
from WorkAI.knowledge_base.lookup import clear_lookup_cache
from WorkAI.knowledge_base.models import KnowledgeArticleDocument, KnowledgeIndexResult
from WorkAI.knowledge_base.queries import replace_article_chunks, upsert_articles_batch

DEFAULT_KNOWLEDGE_SOURCE_DIR = Path("/etc/workai/knowledge/sources")
_LOG = get_logger(__name__)


def index_knowledge_sources(
    settings: Settings | None = None,
    *,
    source_dir: Path | str | None = None,
) -> KnowledgeIndexResult:
    """Index supported methodology files into knowledge_base_articles with soft-sync policy."""

    resolved = settings or get_settings()
    configure_logging(resolved)

    sources_root = Path(source_dir) if source_dir is not None else DEFAULT_KNOWLEDGE_SOURCE_DIR
    if sources_root.exists() and sources_root.is_dir():
        source_files = sorted(
            path
            for path in sources_root.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_KNOWLEDGE_EXTENSIONS
        )
    else:
        source_files = []

    files_seen = len(source_files)
    rows_upserted = 0
    chunks_upserted = 0
    errors_count = 0
    articles: list[KnowledgeArticleDocument] = []

    for path in source_files:
        try:
            articles.append(parse_article_document(path))
        except Exception as exc:
            errors_count += 1
            _LOG.exception(
                "knowledge_index_file_failed",
                source_path=str(path),
                error_type=type(exc).__name__,
            )

    init_db(resolved)
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                rows_upserted = upsert_articles_batch(cur, articles)
                for article in articles:
                    source_chunks = chunk_text(article.body)
                    chunks_upserted += replace_article_chunks(cur, article.source_path, source_chunks)
            conn.commit()
    finally:
        close_db()

    clear_lookup_cache()

    _LOG.info(
        "knowledge_index_completed",
        source_dir=str(sources_root),
        files_seen=files_seen,
        rows_upserted=rows_upserted,
        chunks_upserted=chunks_upserted,
        errors_count=errors_count,
        sync_policy="soft",
    )

    return KnowledgeIndexResult(
        files_seen=files_seen,
        rows_upserted=rows_upserted,
        chunks_upserted=chunks_upserted,
        errors_count=errors_count,
    )


def parse_markdown_article(path: Path) -> KnowledgeArticleDocument:
    """Backward-compatible markdown parser entrypoint."""

    from WorkAI.knowledge_base.extractors import parse_markdown_article as _parse_markdown_article

    return _parse_markdown_article(path)
