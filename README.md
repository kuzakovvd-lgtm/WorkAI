# WorkAI

Employee quality & audit system — v2 modular rewrite.

**Status:** Phase 12 — Hardening.

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

## Normalize (Phase 4)

Normalize слой детерминированно преобразует `raw_tasks` в `tasks_normalized`.

- Источник архитектурного контракта: `ARCHITECTURE.md` (`normalize -> tasks_normalized`).
- TODO(TZ §5): сверить расширенный normalize-контракт с полным внешним ТЗ.

Запуск normalize вручную:

```bash
python scripts/workai_normalize.py run
```

Минимальные переменные:

- `WORKAI_NORMALIZE__ENABLED=true`
- `WORKAI_GSHEETS__SPREADSHEET_ID=<spreadsheet-id>`

Опциональные переменные:

- `WORKAI_NORMALIZE__EMPLOYEE_ALIASES_FILE=/path/to/employee-aliases.csv`
- `WORKAI_NORMALIZE__FUZZY_ENABLED=false|true`
- `WORKAI_NORMALIZE__FUZZY_THRESHOLD=90`
- `WORKAI_NORMALIZE__TIME_PARSE_ENABLED=true|false`
- `WORKAI_NORMALIZE__CATEGORY_RULES_FILE=/path/to/category-rules.json`
- `WORKAI_NORMALIZE__MAX_ERRORS_PER_SHEET=50`

## Pre-flight hardening (Phase 4.5)

- Integration CI now includes ephemeral PostgreSQL job (`pytest -m integration`).
- Normalize writes record-level failures to `pipeline_errors`.
- Normalize full-refresh runs with advisory lock single-flight per `(spreadsheet_id, sheet_title, work_date)`.
- Assess-like query plan baseline can be generated via:

```bash
python scripts/workai_explain_assess.py --date 2026-04-07
```

## Knowledge Base (Phase 6)

Knowledge Base indexes methodology markdown files into PostgreSQL and provides FTS lookup.

- Source directory (default): `/etc/workai/knowledge/sources/*.md`
- Sync strategy (MVP): **soft-sync** (missing files are not deleted from DB).
- Lookup SQL uses PostgreSQL FTS primitives:
  - `websearch_to_tsquery('russian', ...)`
  - `ts_rank(...)`

Run indexer:

```bash
python scripts/run_index_knowledge.py run
python scripts/run_index_knowledge.py run --source-dir /tmp/workai-knowledge
```

Lookup from Python:

```python
from WorkAI.knowledge_base import lookup_methodology
results = lookup_methodology("ghost time", limit=5)
```

Notes:

- Lookup uses LRU cache (`maxsize=100`) keyed by `(query, limit)`.
- Cache is explicitly cleared after each indexing run.

## AI Audit (Phase 7)

Audit layer runs a sequential 3-agent CrewAI flow and stores results in `audit_runs`.

- Agents:
  - Operational Efficiency Analyst (`gpt-4o-mini`)
  - Data Integrity Forensic (`gpt-4o-mini`)
  - Strategic Management Reporter (`gpt-4o`)
- Models are configured only via ENV/settings (`OPENAI_MODEL_*`).
- Runner contract:
  - `run_audit(employee_id, task_date, force=False)`
  - cache semantics via `completed`/`completed_cached`
  - usage telemetry saved under `report_json._usage`

Run audit from CLI:

```bash
python scripts/run_audit.py run --employee-id 42 --date 2026-04-09
python scripts/run_audit.py run --employee-id 42 --date 2026-04-09 --force
```

## API (Phase 8)

FastAPI app now exposes HTTP endpoints for health, tasks, analysis, team and debug reads.

- App import path: `WorkAI.api.main:app`
- Version header: `X-WorkAI-Version: 2.0.0`
- Auth: `X-API-Key` required for all endpoints except `GET /health`
- Blocking operations are executed via `asyncio.to_thread(...)`

Run API server:

```bash
python scripts/workai_api.py run --host 127.0.0.1 --port 8000
# or
uvicorn WorkAI.api.main:app
```

Required API env:

- `WORKAI_API_KEY=<secret>`
- `WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai`

## Notifier (Phase 9)

Notifier sends Telegram alerts by severity and logs **every** attempt into
`notification_log`.

Required env:

- `WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai`
- `TELEGRAM_BOT_TOKEN=<secret>`
- `TELEGRAM_ADMIN_CHAT_ID=<chat-id>`
- `TELEGRAM_MGMT_CHAT_ID=<chat-id>`
- optional: `TELEGRAM_INFO_CHAT_ID=<chat-id>`

Run notifier smoke:

```bash
python scripts/run_notifier_smoke.py send-test --level info --subject "Notifier smoke" --body "phase-9"
```

Severity routing (MVP):

- `infra_critical` -> admin chat
- `data_warning` -> management chat
- `info` -> info chat if set, otherwise admin fallback

## Operations (Phase 10)

Ops layer adds reproducible maintenance routines and operational checks:

- healthcheck with severity (`info`, `data_warning`, `infra_critical`)
- stale sweeper for long-running `audit_runs`
- daily cost rollup from `audit_runs.report_json._usage` into `audit_cost_daily`
- systemd unit ExecStart path verification

Run ops entrypoints:

```bash
python scripts/run_healthcheck.py --unit-dir /etc/systemd/system
python scripts/run_stale_sweeper.py --threshold-minutes 15
python scripts/run_cost_rollup.py --date 2026-04-09
python scripts/run_verify_units.py --unit-dir /etc/systemd/system
```

`run_healthcheck.py` exit codes:

- `0` -> info/ok
- `1` -> data_warning
- `2` -> infra_critical

## Migration & Cutover (Phase 11)

Phase 11 is officially re-scoped to **v2-first safe production launch**.

Decision summary:

- original v1-migration criteria are waived by explicit project decision;
- validation no longer depends on v1 alignment gates;
- rollback target is previous v2 deploy/DB snapshot, not v1 runtime.

Phase 11 now focuses on reproducible v2 launch artifacts:

- `deploy/systemd/workai-*.service` and `workai-*.timer` templates
- production secrets contract in `deploy/secrets.example/`
- launch/readiness helpers and runbook
- cutover readiness checker and runbook

Run migration helpers:

```bash
python scripts/run_cutover_readiness.py
python scripts/run_parallel_diff.py \
  --date 2026-04-09 \
  --reference-json /tmp/workai-launch-baseline-counts-2026-04-09.json \
  --tolerance-pct 5
```

Canonical production path policy:

- target: `/opt/workai`
- current legacy dev path may still be `/opt/WorkAI` during transition.
- see `CUTOVER.md` for alignment and rollback procedure.

## Hardening (Phase 12)

Phase 12 focuses on quality and operational hardening without adding new product
features.

Main checks:

```bash
scripts/run_phase12_hardening_checks.sh
```

Performance baseline generation:

```bash
python scripts/run_phase12_benchmarks.py --rows 200 --cols 40 --sheets 3
```

Disaster recovery plan:

- see `docs/DR_PLAN.md`.

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
