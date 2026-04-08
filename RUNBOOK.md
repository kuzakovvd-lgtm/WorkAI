# WorkAI Runbook

## Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

## Standard verification

```bash
ruff check .
mypy WorkAI
pytest
```

## Database environment

Required minimum:

- `WORKAI_DB__DSN`
- `WORKAI_DB__LOCK_TIMEOUT_MS` (default `2000`)

Optional pool tuning:

- `WORKAI_DB__MIN_SIZE`
- `WORKAI_DB__MAX_SIZE`
- `WORKAI_DB__TIMEOUT_SEC`
- `WORKAI_DB__CONNECT_TIMEOUT_SEC`

## Migrations

```bash
export WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai
python scripts/workai_migrate.py upgrade head
python scripts/workai_migrate.py current
python scripts/workai_migrate.py downgrade -1
```

Offline SQL generation:

```bash
WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai alembic upgrade head --sql
```

## Connectivity smoke test

```bash
pytest tests/integration/test_db_connectivity.py
```

## Ingest run (Phase 2)

```bash
export WORKAI_GSHEETS__ENABLED=true
export WORKAI_GSHEETS__SPREADSHEET_ID=<spreadsheet-id>
export WORKAI_GSHEETS__RANGES=Sheet1!A1:Z200,Sheet2!A1:Z200
export WORKAI_GSHEETS__SERVICE_ACCOUNT_FILE=/path/to/service-account.json
python scripts/workai_ingest.py run
```

## Parse run (Phase 3)

```bash
export WORKAI_PARSE__ENABLED=true
export WORKAI_GSHEETS__SPREADSHEET_ID=<spreadsheet-id>
export WORKAI_PARSE__HEADER_ROW_IDX=1
export WORKAI_PARSE__EMPLOYEE_COL_IDX=1
export WORKAI_PARSE__DATE_FORMATS=%Y-%m-%d,%d.%m.%Y
python scripts/workai_parse.py run
```

## Server path conventions

- v2: `/opt/WorkAI`
- v1 (do not modify): `/opt/employee-analytics`
