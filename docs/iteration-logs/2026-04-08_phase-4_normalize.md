# Iteration: Phase 4 normalize (raw_tasks -> tasks_normalized)

- Date: 2026-04-08
- Branch: `main`
- Commit(s): `pending`
- Owner: `codex`
- Status: `completed`

## Input

- Task/requirements: implement deterministic normalize layer converting `raw_tasks` into `tasks_normalized` as DB contract for assess phase.
- Constraints:
  - strict typing/lint/tests,
  - no DB side effects on import,
  - no secrets in repo,
  - no heavy ORM/runtime dependencies.
- Non-goals: assess scoring/business judgments beyond normalization contract.

## Plan

1. Add migration `0004_tasks_normalized` and update DB contract docs.
2. Extend settings/env templates with `NormalizeSettings`.
3. Implement normalize package (text/time/employee/category/queries/runner) and CLI script.
4. Add unit/integration tests and validate full toolchain.

## Changes

### Files added

- Normalize runtime:
  - `WorkAI/normalize/models.py`
  - `WorkAI/normalize/text_norm.py`
  - `WorkAI/normalize/time_parse.py`
  - `WorkAI/normalize/employee_map.py`
  - `WorkAI/normalize/categorizer.py`
  - `WorkAI/normalize/queries.py`
  - `WorkAI/normalize/runner.py`
- Migration:
  - `migrations/versions/0004_tasks_normalized.py`
- CLI:
  - `scripts/workai_normalize.py`
- Tests:
  - `tests/unit/test_normalize_text.py`
  - `tests/unit/test_normalize_time_parse.py`
  - `tests/unit/test_normalize_employee_map.py`
  - `tests/unit/test_normalize_categorizer.py`
  - `tests/integration/test_normalize_smoke.py`

### Files updated

- `WorkAI/config/settings.py` (`NormalizeSettings` and validators).
- `WorkAI/config/__init__.py` (export `NormalizeSettings`).
- `WorkAI/normalize/__init__.py` (export `run_normalize`).
- `.env.example`, `deploy/secrets.example/workai.env.example` (`WORKAI_NORMALIZE__*`).
- `DB_CONTRACT.md`, `README.md`, `RUNBOOK.md`, `ROADMAP.md`, `TASK_BOARD.md`, `ARCHITECTURE.md`.
- `DECISIONS.md` (ADR-0006 and ADR-0007).
- `tests/unit/test_settings.py` (normalize settings coverage).

### Files removed

- None.

## Validation

### Automatic checks

- `.venv/bin/ruff check .`: passed.
- `.venv/bin/mypy WorkAI`: passed.
- `.venv/bin/pytest`: passed (`35 passed, 4 skipped`).

### Manual checks

- `WORKAI_NORMALIZE__ENABLED=false .venv/bin/python scripts/workai_normalize.py run`: no-op with `normalize_disabled` log.
- `WORKAI_DB__DSN=postgresql://user:pass@127.0.0.1:5432/workai .venv/bin/alembic upgrade head --sql` includes `0004_tasks_normalized` DDL.

## Decisions and rationale

- Normalize idempotency strategy: full-refresh per sheet (`DELETE tasks_normalized for sheet -> INSERT normalized rows`).
- Employee matching order is deterministic: exact -> alias -> optional fuzzy (`difflib`) -> fallback.
- Time extraction is strict regex-based to keep behavior deterministic and debuggable.

## Risks / caveats

- Online migration and normalize smoke require live PostgreSQL credentials.
- Fuzzy matching quality in MVP is limited by stdlib `difflib`; may require optional upgrade later.

## Next step

- Phase 5 assess layer (`tasks_normalized` -> `daily_task_assessments`).
