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

## Normalize run (Phase 4)

```bash
export WORKAI_NORMALIZE__ENABLED=true
export WORKAI_GSHEETS__SPREADSHEET_ID=<spreadsheet-id>
export WORKAI_NORMALIZE__EMPLOYEE_ALIASES_FILE=/path/to/employee-aliases.csv
export WORKAI_NORMALIZE__FUZZY_ENABLED=false
export WORKAI_NORMALIZE__FUZZY_THRESHOLD=90
export WORKAI_NORMALIZE__TIME_PARSE_ENABLED=true
export WORKAI_NORMALIZE__CATEGORY_RULES_FILE=/path/to/category-rules.json
export WORKAI_NORMALIZE__MAX_ERRORS_PER_SHEET=50
python scripts/workai_normalize.py run
```

Normalize concurrency policy:

- Full-refresh is partitioned by `(spreadsheet_id, sheet_title, work_date)`.
- Single-flight is enforced by PostgreSQL advisory lock:
  `normalize|<spreadsheet_id>:<sheet_title>|<work_date>`.
- If lock is not acquired, runner logs `normalize_lock_not_acquired` and skips that partition.
- Skip without retry is intentional in Phase 4.5.
- Operational threshold: if one partition is skipped in more than 3 scheduled runs in a row,
  trigger manual re-run and investigate overlapping scheduler windows or stuck workers.

## Pipeline errors (DLQ-style)

Inspect latest normalize errors:

```bash
psql "$WORKAI_DB__DSN" -c "
SELECT id, run_id, sheet_id, work_date, source_ref, error_type, left(error_message, 120) AS error_message, created_at
FROM pipeline_errors
WHERE phase = 'normalize'
ORDER BY created_at DESC
LIMIT 50;
"
```

Reprocess strategy:

- fix mapping/rules/root cause,
- rerun normalize for the same source spreadsheet/date,
- confirm new run_id has no new `pipeline_errors` rows for affected source_ref values.

Retention policy (MVP):

- keep `pipeline_errors` for 90 days;
- run manual cleanup weekly until ops automation exists;
- move automated cleanup to Phase 10 (ops).

Cleanup SQL (batch):

```bash
psql "$WORKAI_DB__DSN" -c "
DELETE FROM pipeline_errors
WHERE id IN (
  SELECT id
  FROM pipeline_errors
  WHERE created_at < now() - interval '90 days'
  ORDER BY created_at
  LIMIT 5000
);
"
```

## Assess EXPLAIN pre-check

Generate assess-like query plans:

```bash
python scripts/workai_explain_assess.py --date 2026-04-07
python scripts/workai_explain_assess.py --date 2026-04-07 --sheet-id Sheet1
```

Output is written to `docs/perf/assess_explain_<YYYY-MM-DD>.md`.

## Server path conventions

- v2: `/opt/WorkAI`
- v1 (do not modify): `/opt/employee-analytics`
