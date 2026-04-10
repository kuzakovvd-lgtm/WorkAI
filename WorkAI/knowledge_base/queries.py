"""SQL helpers for knowledge base indexing and lookup."""

from __future__ import annotations

from collections.abc import Sequence

from psycopg import Cursor
from psycopg.errors import UndefinedTable

from WorkAI.knowledge_base.models import KnowledgeArticleDocument, KnowledgeSearchResult

UPSERT_ARTICLE_SQL = """
INSERT INTO knowledge_base_articles (
    source_path,
    title,
    body,
    tags,
    indexed_at
)
VALUES (%s, %s, %s, %s, now())
ON CONFLICT (source_path)
DO UPDATE SET
    title = EXCLUDED.title,
    body = EXCLUDED.body,
    tags = EXCLUDED.tags,
    indexed_at = now()
"""

LOOKUP_METHODOLOGY_SQL = """
WITH q AS (
    SELECT websearch_to_tsquery('russian', %s) AS query
)
SELECT
    a.source_path,
    a.title,
    c.chunk_text AS body,
    a.tags,
    ts_rank(c.fts, q.query) AS rank
FROM knowledge_base_chunks AS c
JOIN knowledge_base_articles AS a ON a.source_path = c.source_path
CROSS JOIN q
WHERE c.fts @@ q.query
ORDER BY rank DESC, a.source_path ASC, c.chunk_no ASC
LIMIT %s
"""

LOOKUP_METHODOLOGY_FALLBACK_SQL = """
WITH q AS (
    SELECT websearch_to_tsquery('russian', %s) AS query
)
SELECT
    a.source_path,
    a.title,
    a.body,
    a.tags,
    ts_rank(a.fts, q.query) AS rank
FROM knowledge_base_articles AS a
CROSS JOIN q
WHERE a.fts @@ q.query
ORDER BY rank DESC, a.source_path ASC
LIMIT %s
"""

DELETE_CHUNKS_BY_SOURCES_SQL = """
DELETE FROM knowledge_base_chunks
WHERE source_path = ANY(%s)
"""

INSERT_CHUNKS_SQL = """
INSERT INTO knowledge_base_chunks (
    source_path,
    chunk_no,
    chunk_text,
    indexed_at
)
VALUES (%s, %s, %s, now())
"""

COUNT_ARTICLES_SQL = """
SELECT count(*)::int
FROM knowledge_base_articles
"""


def upsert_articles_batch(
    cursor: Cursor[tuple[object, ...]],
    rows: Sequence[KnowledgeArticleDocument],
) -> int:
    """Upsert parsed markdown articles by source_path."""

    if not rows:
        return 0

    cursor.executemany(
        UPSERT_ARTICLE_SQL,
        [(row.source_path, row.title, row.body, row.tags) for row in rows],
    )
    return len(rows)


def lookup_articles(
    cursor: Cursor[tuple[str, str, str, list[str], float]],
    query: str,
    limit: int,
    *,
    excerpt_chars: int = 240,
) -> list[KnowledgeSearchResult]:
    """Perform FTS lookup using websearch_to_tsquery + ts_rank."""

    try:
        cursor.execute(LOOKUP_METHODOLOGY_SQL, (query, limit))
    except UndefinedTable:
        cursor.execute(LOOKUP_METHODOLOGY_FALLBACK_SQL, (query, limit))
    rows = cursor.fetchall()

    results: list[KnowledgeSearchResult] = []
    for source_path, title, body, tags, rank in rows:
        body_text = str(body).strip()
        excerpt = body_text[:excerpt_chars]
        results.append(
            KnowledgeSearchResult(
                source_path=str(source_path),
                title=str(title),
                body_excerpt=excerpt,
                tags=[str(item) for item in tags],
                rank=float(rank),
            )
        )
    return results


def replace_article_chunks(
    cursor: Cursor[tuple[object, ...]],
    source_path: str,
    chunks: Sequence[str],
) -> int:
    """Replace stored chunks for one source_path."""

    cursor.execute(DELETE_CHUNKS_BY_SOURCES_SQL, ([source_path],))
    if not chunks:
        return 0

    cursor.executemany(
        INSERT_CHUNKS_SQL,
        [(source_path, index + 1, chunk) for index, chunk in enumerate(chunks)],
    )
    return len(chunks)


def count_articles(cursor: Cursor[tuple[int]]) -> int:
    """Return indexed article count."""

    cursor.execute(COUNT_ARTICLES_SQL)
    row = cursor.fetchone()
    if row is None:
        return 0
    return int(row[0])
