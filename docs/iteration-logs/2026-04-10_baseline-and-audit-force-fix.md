# Iteration Log — 2026-04-10 — Baseline freeze + audit force-path fix

## Scope

- Freeze production-like v2 baseline from live Google Sheets.
- Document runtime assumptions and baseline counters.
- Fix `run_audit --force` pool lifecycle bug in error-path.

## Baseline captured

- Runtime path: `/opt/workai -> /opt/WorkAI`
- Branch: `Itogmain`
- Counters:
  - `sheet_cells = 31376`
  - `raw_tasks = 1892`
  - `tasks_normalized = 1892`
  - `daily_task_assessments = 39`
  - `operational_cycles = 39`
  - `audit_runs = 4`

## Technical changes

- Parse weekly-board fallback documented as active baseline behavior.
- `WorkAI/knowledge_base/lookup.py`:
  - removed `close_db()` from cached lookup path to avoid closing shared pool during audit tool calls.
- `WorkAI/audit/crew.py`:
  - added resilient failed-run persistence helper with one `init_db()` retry on `DatabaseError`.
- Added regression test:
  - `tests/unit/test_audit_force_error_path.py`
  - validates force error-path when pool is closed mid-run and ensures failed status persistence logic runs.

## Validation

- Local static/test commands executed after patch:
  - `ruff check .`
  - `mypy WorkAI`
  - `pytest -q`
- Server smoke:
  - ingest/parse/normalize/assess/audit/notifier health path verified with non-empty pipeline data.

## Notes

- Baseline documentation includes historical caveat that force-path bug existed at capture time.
- Hotfix in this iteration closes that gap without changing success-path semantics.
