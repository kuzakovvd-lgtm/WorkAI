# Phase 6 — Knowledge Base (2026-04-09)

## Scope

Implement Knowledge Base MVP:

- DB contract table `knowledge_base_articles`.
- Markdown indexer (`*.md` -> DB UPSERT).
- PostgreSQL FTS lookup (`websearch_to_tsquery`, `ts_rank`).
- LRU cache for lookup (`maxsize=100`).
- CLI entrypoint for indexing.
- Unit/integration tests.

## Decisions

- Sync strategy: **soft-sync** (missing source files are not deleted from DB).
- Cache strategy: function-level LRU `(query, limit)`, explicit clear after index run.
- No external vector DB / embeddings / LLM indexing.

## Files changed

- `migrations/versions/0012_knowledge_base_articles.py`
- `WorkAI/knowledge_base/__init__.py`
- `WorkAI/knowledge_base/models.py`
- `WorkAI/knowledge_base/queries.py`
- `WorkAI/knowledge_base/indexer.py`
- `WorkAI/knowledge_base/lookup.py`
- `scripts/run_index_knowledge.py`
- `tests/unit/test_knowledge_indexer.py`
- `tests/unit/test_knowledge_lookup.py`
- `tests/integration/test_knowledge_base_smoke.py`
- `README.md`
- `DB_CONTRACT.md`
- `RUNBOOK.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `TASK_BOARD.md`
- `docs/iteration-logs/README.md`
- `DECISIONS.md`

## Validation plan

- `ruff check .`
- `mypy WorkAI`
- `pytest`
- `pytest -m integration` (requires `WORKAI_DB__DSN`)
- `alembic upgrade head --sql`

## Notes

- TODO(TZ §6.3): when full external spec is available, align metadata extraction and retention/cleanup policy.
