# WorkAI

Employee quality & audit system — v2 modular rewrite.

**Status:** Phase 1 — Core infrastructure.

## What it does

Pipeline: ingest Google Sheets -> parse workday maps -> normalize tasks ->
assess effort & ghost time -> multi-agent AI audit (CrewAI) -> REST API +
Telegram reports.

See `ARCHITECTURE.md` for details. Full product specification is maintained
separately by the project owner.

## Requirements

- Python 3.12+
- PostgreSQL 15+
- Linux (systemd for production deployment)

## Development setup

```bash
git clone https://github.com/kuzakovvd-lgtm/WorkAI.git
cd WorkAI
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# Verify
python -c "import WorkAI; print(WorkAI.__version__)"
ruff check .
mypy WorkAI
pytest
```

## Database & migrations (Phase 1)

Required environment variables:

- `WORKAI_ENV=dev|staging|prod`
- `WORKAI_LOG__LEVEL=DEBUG|INFO|WARNING|ERROR`
- `WORKAI_LOG__JSON=false|true`
- `WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai`
- `WORKAI_DB__MIN_SIZE=1`
- `WORKAI_DB__MAX_SIZE=5`
- `WORKAI_DB__TIMEOUT_SEC=10`
- `WORKAI_DB__CONNECT_TIMEOUT_SEC=5`
- `WORKAI_DB__LOCK_TIMEOUT_MS=2000`

Migration commands:

```bash
export WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai
python scripts/workai_migrate.py upgrade head
python scripts/workai_migrate.py current
python scripts/workai_migrate.py downgrade -1
alembic upgrade head --sql
```

Run integration connectivity test locally:

```bash
export WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai
pytest tests/integration/test_db_connectivity.py
```

## Project structure

```text
WorkAI/           Python package (modular pipeline)
├── ingest/       Google Sheets -> sheet_cells
├── parse/        sheet_cells -> raw_tasks
├── normalize/    raw_tasks -> tasks_normalized
├── assess/       scoring, ghost time, norms
├── audit/        CrewAI multi-agent audit
├── knowledge_base/  FTS methodology search
├── notifier/     Telegram alerting
├── db/           Connection pool & schema
├── api/          FastAPI REST endpoints
├── ops/          Healthcheck, sweepers, rollups
├── config/       Settings & secrets
└── common/       Shared utilities

scripts/          systemd entrypoints
tests/            unit / integration / smoke
sql/              SQL snapshots and helpers
migrations/       Alembic revisions
deploy/           systemd units & secret templates
docs/             Architecture & ops documentation
```

## Iteration logs

Detailed implementation logs for each phase are stored in
`docs/iteration-logs/`.

## Documentation index

Use `DOCS_INDEX.md` as the single entry point for project context.

## License

Proprietary — internal company use only.
