# Iteration: Phase 3 parse (sheet_cells -> raw_tasks)

- Date: 2026-04-08
- Branch: `main`
- Commit(s): `e0a33bf`
- Owner: `codex`
- Status: `completed`

## Input

- Task/requirements: implement deterministic parse layer converting `sheet_cells` into `raw_tasks` as DB contract for normalize phase.
- Constraints:
  - strict typing/lint/tests,
  - no DB side effects on import,
  - no secrets in repo,
  - no dependency on Google API for parse testability.
- Non-goals: normalize/business semantics beyond raw line extraction.

## Plan

1. Add migration `0003_raw_tasks` and update DB contract docs.
2. Add parse settings and env templates.
3. Implement parse package (date/layout/parser/queries/runner) and CLI script.
4. Add unit/integration tests and validate full toolchain.

## Changes

### Files added

- Parse runtime:
  - `WorkAI/parse/models.py`
  - `WorkAI/parse/date_parse.py`
  - `WorkAI/parse/layout.py`
  - `WorkAI/parse/parser.py`
  - `WorkAI/parse/queries.py`
  - `WorkAI/parse/runner.py`
- Migration:
  - `migrations/versions/0003_raw_tasks.py`
- CLI:
  - `scripts/workai_parse.py`
- Tests:
  - `tests/unit/test_parse_dates.py`
  - `tests/unit/test_parse_layout.py`
  - `tests/unit/test_parse_cells.py`
  - `tests/integration/test_parse_smoke.py`

### Files updated

- `WorkAI/config/settings.py` (`ParseSettings` and validators).
- `WorkAI/config/__init__.py` (export `ParseSettings`).
- `WorkAI/parse/__init__.py` (export `run_parse`).
- `.env.example`, `deploy/secrets.example/workai.env.example` (`WORKAI_PARSE__*`).
- `DB_CONTRACT.md`, `README.md`, `RUNBOOK.md`, `ROADMAP.md`, `TASK_BOARD.md`, `ARCHITECTURE.md`.
- `DECISIONS.md` (ADR about full-refresh idempotency).
- `tests/unit/test_settings.py` (parse settings coverage).

### Files removed

- None.

## Validation

### Automatic checks

- `ruff check .`: passed.
- `mypy WorkAI`: passed (strict).
- `pytest`: passed (`22 passed, 3 skipped`, integration skips depend on env).

### Manual checks

- `WORKAI_PARSE__ENABLED=false python scripts/workai_parse.py run`: no-op with `parse_disabled` log.
- `WORKAI_DB__DSN=... alembic upgrade head --sql` includes `0003_raw_tasks` DDL.

## Decisions and rationale

- Parse idempotency strategy: full refresh per sheet (`DELETE raw_tasks for sheet -> INSERT parsed rows`).
- Parser is deterministic by sorting input cells and preserving line order inside each cell.
- Layout/date extraction isolated in pure functions for unit-level validation.

## Risks / caveats

- Online migration and parse smoke require live PostgreSQL credentials.
- Date parsing intentionally strict (configured `strptime` formats only).

## Next step

- Phase 4 normalize layer (`raw_tasks` -> `tasks_normalized`).
