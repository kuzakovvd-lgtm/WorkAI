"""Knowledge base indexer for markdown methodology sources."""

from __future__ import annotations

import json
from pathlib import Path

from WorkAI.common import configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.knowledge_base.lookup import clear_lookup_cache
from WorkAI.knowledge_base.models import KnowledgeArticleDocument, KnowledgeIndexResult
from WorkAI.knowledge_base.queries import upsert_articles_batch

DEFAULT_KNOWLEDGE_SOURCE_DIR = Path("/etc/workai/knowledge/sources")
_LOG = get_logger(__name__)


def index_knowledge_sources(
    settings: Settings | None = None,
    *,
    source_dir: Path | str | None = None,
) -> KnowledgeIndexResult:
    """Index markdown files into knowledge_base_articles with soft-sync policy."""

    resolved = settings or get_settings()
    configure_logging(resolved)

    sources_root = Path(source_dir) if source_dir is not None else DEFAULT_KNOWLEDGE_SOURCE_DIR
    markdown_files = sorted(path for path in sources_root.glob("*.md") if path.is_file())

    files_seen = len(markdown_files)
    rows_upserted = 0
    errors_count = 0
    articles: list[KnowledgeArticleDocument] = []

    for path in markdown_files:
        try:
            articles.append(parse_markdown_article(path))
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
            conn.commit()
    finally:
        close_db()

    clear_lookup_cache()

    _LOG.info(
        "knowledge_index_completed",
        source_dir=str(sources_root),
        files_seen=files_seen,
        rows_upserted=rows_upserted,
        errors_count=errors_count,
        sync_policy="soft",
    )

    return KnowledgeIndexResult(
        files_seen=files_seen,
        rows_upserted=rows_upserted,
        errors_count=errors_count,
    )


def parse_markdown_article(path: Path) -> KnowledgeArticleDocument:
    """Parse one markdown file into article payload."""

    content = path.read_text(encoding="utf-8")
    metadata, markdown_body = _split_frontmatter(content)

    title, body = _extract_title_and_body(markdown_body, fallback_title=path.stem)
    tags = _extract_tags(metadata)

    return KnowledgeArticleDocument(
        source_path=str(path),
        title=title,
        body=body,
        tags=tags,
    )


def _split_frontmatter(content: str) -> tuple[dict[str, object], str]:
    text = content.lstrip("\ufeff")
    if not text.startswith("---\n"):
        return {}, content

    end_marker = "\n---\n"
    end_index = text.find(end_marker, 4)
    if end_index == -1:
        return {}, content

    raw_meta = text[4:end_index]
    body = text[end_index + len(end_marker) :]
    metadata: dict[str, object] = {}

    for line in raw_meta.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        metadata[key.strip().lower()] = value.strip()

    return metadata, body


def _extract_title_and_body(markdown_body: str, *, fallback_title: str) -> tuple[str, str]:
    lines = markdown_body.splitlines()
    title = fallback_title
    body_lines = lines

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            candidate = stripped[2:].strip()
            if candidate:
                title = candidate
            body_lines = lines[:index] + lines[index + 1 :]
            break

    body = "\n".join(body_lines).strip()
    return title, body


def _extract_tags(metadata: dict[str, object]) -> list[str]:
    raw = metadata.get("tags")
    if raw is None:
        return []

    if isinstance(raw, str):
        candidate = raw.strip()
        if candidate.startswith("[") and candidate.endswith("]"):
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass

        return [part.strip() for part in candidate.split(",") if part.strip()]

    return []
