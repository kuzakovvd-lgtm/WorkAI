# Iteration: Phase 2 ingest (Google Sheets -> sheet_cells)

- Date: 2026-04-08
- Branch: `main`
- Commit(s): `ea4c926`
- Owner: `codex`
- Status: `completed`

## Input

- Task/requirements: implement ingest layer with Google Sheets read-only API integration and idempotent persistence into `sheet_cells`.
- Constraints:
  - no DB side effects on import,
  - no secrets in repository,
  - keep dependency direction,
  - bounded A1 ranges only,
  - CI must work without Google/DB.
- Non-goals: parse/normalize business logic and full schema expansion beyond `sheet_cells`.

## Plan

1. Add Google API dependencies and settings model (`gsheets`).
2. Add Alembic migration for `sheet_cells` and ingest runtime modules.
3. Add CLI script, unit tests, integration smoke tests (skip by env).
4. Update docs and run full checks.

## Changes

### Files added

- Ingest runtime:
  - `WorkAI/ingest/a1.py`
  - `WorkAI/ingest/models.py`
  - `WorkAI/ingest/sheets_client.py`
  - `WorkAI/ingest/runner.py`
- Migration:
  - `migrations/versions/0002_sheet_cells.py`
- CLI:
  - `scripts/workai_ingest.py`
- Tests:
  - `tests/unit/test_a1.py`
  - `tests/unit/test_ingest_flatten.py`
  - `tests/integration/test_ingest_smoke.py`

### Files updated

- `pyproject.toml` (Google dependencies).
- `WorkAI/config/settings.py` (`GoogleSheetsSettings` + validators).
- `WorkAI/config/__init__.py` (export `GoogleSheetsSettings`).
- `WorkAI/ingest/__init__.py` (public API export).
- `.env.example`, `deploy/secrets.example/workai.env.example` (new `WORKAI_GSHEETS__*`).
- `README.md` (Phase 2 ingest usage).
- `tests/unit/test_settings.py` (gsheets validation coverage).

### Files removed

- None.

## Validation

### Automatic checks

- `pip install -e ".[dev]"`: passed.
- `ruff check .`: passed.
- `mypy WorkAI`: passed (strict).
- `pytest`: passed (`14 passed, 2 skipped`).

### Manual checks

- Ingest CLI no-op mode:
  - `WORKAI_GSHEETS__ENABLED=false python scripts/workai_ingest.py run`
  - result: clean no-op with structured log `ingest_disabled`.
- Alembic offline SQL for Phase 2:
  - `WORKAI_DB__DSN=... alembic upgrade head --sql`
  - output includes `CREATE TABLE sheet_cells` and revision transition to `0002_sheet_cells`.

## Decisions and rationale

- Idempotency strategy: `DELETE` target range area then `INSERT` only non-empty cells.
- Deletions in source are reflected by clearing full range window before insert.
- Google API calls use `batchGet` with chunked ranges and retry/backoff for transient failures.
- A1 parser explicitly rejects unbounded ranges to prevent accidental huge ingestion.

## Risks / caveats

- Online migration apply/rollback against real PostgreSQL was not executed in this iteration due missing DB credentials in workspace.
- Integration ingest test intentionally skips unless DB + Google env are provided.
- TODO markers added where full external spec is needed:
  - `TODO(TZ §2.1)` in ingest runner,
  - `TODO(TZ §3.2)` in migration,
  - `TODO(TZ §2.2)` in README.

## Next step

- Phase 3 parse layer implementation on top of `sheet_cells -> raw_tasks` contract.
