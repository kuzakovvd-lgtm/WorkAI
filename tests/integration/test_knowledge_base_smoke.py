from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from WorkAI.config import get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.knowledge_base import index_knowledge_sources, lookup_methodology


@pytest.mark.integration
def test_knowledge_base_index_and_lookup_smoke(tmp_path: Path) -> None:
    dsn = os.getenv("WORKAI_DB__DSN", "").strip()
    if not dsn:
        pytest.skip("WORKAI_DB__DSN is not set")

    os.environ["WORKAI_GSHEETS__ENABLED"] = "false"
    os.environ["WORKAI_PARSE__ENABLED"] = "false"
    os.environ["WORKAI_NORMALIZE__ENABLED"] = "false"
    get_settings.cache_clear()

    source_dir = tmp_path / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)

    (source_dir / "ghost_time.md").write_text(
        "# Ghost Time Method\n\n"
        "Detect ghost time by comparing logged duration and expected workday windows.\n",
        encoding="utf-8",
    )
    (source_dir / "quality.md").write_text(
        "---\n"
        "tags: quality, trust\n"
        "---\n"
        "# Quality Notes\n\n"
        "Quality score depends on time source and result confirmation.\n",
        encoding="utf-8",
    )

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM knowledge_base_articles")
            conn.commit()
    finally:
        close_db()

    first = index_knowledge_sources(source_dir=source_dir)
    second = index_knowledge_sources(source_dir=source_dir)

    assert first.files_seen == 2
    assert first.rows_upserted == 2
    assert first.chunks_upserted >= 2
    assert first.errors_count == 0

    assert second.files_seen == 2
    assert second.rows_upserted == 2
    assert second.chunks_upserted >= 2
    assert second.errors_count == 0

    results = lookup_methodology("ghost time", limit=5)
    assert len(results) >= 1
    assert any("ghost" in item.title.lower() or "ghost" in item.body_excerpt.lower() for item in results)

    init_db()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM knowledge_base_articles")
            row = cur.fetchone()
            cur.execute("SELECT count(*) FROM knowledge_base_chunks")
            chunks_row = cur.fetchone()
        assert row is not None
        assert chunks_row is not None
        assert int(row[0]) == 2
        assert int(chunks_row[0]) >= 2
    finally:
        close_db()
