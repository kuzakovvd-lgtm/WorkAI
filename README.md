# WorkAI

Employee quality & audit system — v2 modular rewrite.

**Status:** Phase 3 — Parse layer.

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

## Ingest (Phase 2)

WorkAI ingest reads bounded Google Sheets ranges and writes them to `sheet_cells`.

- Source of truth for architecture: `ARCHITECTURE.md` (`ingest -> sheet_cells`)
- TODO(TZ §2.2): align ingest coverage matrix with full product specification.

Required ingest environment variables:

- `WORKAI_GSHEETS__ENABLED=true`
- `WORKAI_GSHEETS__SPREADSHEET_ID=<google_spreadsheet_id>`
- `WORKAI_GSHEETS__RANGES=Sheet1!A1:Z200,Sheet2!A1:Z200`
- one of:
  - `WORKAI_GSHEETS__SERVICE_ACCOUNT_FILE=/path/to/service-account.json`
  - `WORKAI_GSHEETS__SERVICE_ACCOUNT_JSON_B64=<base64-json>`

Run ingest manually:

```bash
python scripts/workai_ingest.py run
```

Google access note:

- Share spreadsheet with service account email as Viewer (read-only mode).
- Use bounded ranges only (`Sheet1!A1:Z200`), avoid unbounded forms (`A:Z`, `A1:Z`) to prevent huge ingest.
- Ingest uses `batchGet` and range chunking, not per-cell API calls, to reduce quota usage.

## Parse (Phase 3)

Parse слой детерминированно преобразует `sheet_cells` в `raw_tasks`.

- Источник архитектурного контракта: `ARCHITECTURE.md` (`parse -> raw_tasks`).
- TODO(TZ §3.4): сверить расширенный парсинг с полным внешним ТЗ.

Запуск parse вручную:

```bash
python scripts/workai_parse.py run
```

Минимальные переменные:

- `WORKAI_PARSE__ENABLED=true`
- `WORKAI_GSHEETS__SPREADSHEET_ID=<spreadsheet-id>`
- `WORKAI_PARSE__HEADER_ROW_IDX=1`
- `WORKAI_PARSE__EMPLOYEE_COL_IDX=1`
- `WORKAI_PARSE__DATE_FORMATS=%Y-%m-%d,%d.%m.%Y`

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
