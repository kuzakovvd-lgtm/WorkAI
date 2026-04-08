# WorkAI

Employee quality & audit system — v2 modular rewrite.

**Status:** Phase 0 — Bootstrap.

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

## License

Proprietary — internal company use only.
