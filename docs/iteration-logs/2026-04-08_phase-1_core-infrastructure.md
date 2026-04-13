# Iteration: Phase 1 core infrastructure

- Date: 2026-04-08
- Branch: `main`
- Commit(s): `566fe8d`
- Owner: `codex`
- Status: `completed`

## Input

- Task/requirements: implement foundation layers (`config`, `common`, `db`), add Alembic baseline, unit/integration tests, README updates.
- Constraints:
  - no DB side effects on import,
  - no secrets in repo,
  - Python 3.12 target,
  - CI independent from real PostgreSQL,
  - keep v1 untouched.
- Non-goals: business schema and domain logic.

## Plan

1. Add minimum dependencies (`alembic`, `psycopg[binary,pool]`).
2. Implement typed settings + structured logging + DB pool/query/introspection helpers.
3. Add Alembic env, baseline migration, migration wrapper script, tests, and docs.
4. Validate locally and on server with Python 3.12.

## Changes

### Files added

- Config:
  - `WorkAI/config/settings.py`
- Common:
  - `WorkAI/common/errors.py`
  - `WorkAI/common/logging.py`
- DB:
  - `WorkAI/db/pool.py`
  - `WorkAI/db/queries.py`
  - `WorkAI/db/schema.py`
- Alembic:
  - `alembic.ini`
  - `migrations/env.py`
  - `migrations/script.py.mako`
  - `migrations/versions/0001_baseline.py`
  - `scripts/workai_migrate.py`
- Env templates:
  - `.env.example`
  - `deploy/secrets.example/workai.env.example`
- Tests:
  - `tests/unit/test_settings.py`
  - `tests/unit/test_logging.py`
  - `tests/integration/test_db_connectivity.py`

### Files updated

- `pyproject.toml` (dependencies + strict tooling coherence).
- `WorkAI/config/__init__.py`, `WorkAI/common/__init__.py`, `WorkAI/db/__init__.py` (public API exports).
- `README.md` (Phase 1 database & migrations section).

### Files removed

- None.

## Validation

### Automatic checks

- `pip install -e ".[dev]"`: passed with new dependencies.
- `ruff check .`: passed.
- `mypy WorkAI`: passed strict.
- `pytest`: passed (`4 passed, 1 skipped`), integration test skipped when `WORKAI_DB__DSN` is absent.

### Manual checks

- Config smoke without DSN:
  - `python -c "from WorkAI.config import get_settings; get_settings.cache_clear(); print(get_settings().app.env)"`
  - result: `dev`.
- Import side-effects check:
  - `python -c "import WorkAI.db; print('import-ok')"`
  - result: `import-ok` (no DB connection attempt).
- Alembic offline SQL generation:
  - `WORKAI_DB__DSN=postgresql://user:pass@localhost:5432/workai alembic upgrade head --sql`
  - result includes baseline DDL for `alembic_version` and revision `0001_baseline`.
- Server validation (`/opt/workai`, Python `3.12.3`):
  - `pip install -e ".[dev]"`, `ruff`, `mypy`, `pytest` all passed.

## Decisions and rationale

- `WORKAI_ENV` retained as top-level canonical env var, then synchronized into `settings.app.env` for compatibility with requested contract.
- Logging JSON flag implemented as internal `json_output` with alias `json` to avoid pydantic method-name shadowing while preserving env contract `WORKAI_LOG__JSON`.
- Alembic baseline created as empty migration (`pass`) because schema DDL was not present in repository scope.

## Risks / caveats

- No online migration applied against real production DB in this iteration (by design); only offline generation and test-ready environment were validated.
- Integration connectivity test remains opt-in via `WORKAI_DB__DSN`.

## Next step

- Phase 2 ingest layer, reusing `config/common/db` foundation and applying real DB schema migrations when schema contract is provided.
