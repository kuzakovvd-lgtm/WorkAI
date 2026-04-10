# Phase 11 — Migration & Cutover Preparation

Date: 2026-04-09
Status: In progress

## Scope

- Prepare v2 deployment artifacts near v1 without touching v1 runtime.
- Add reproducible parallel-run diff helper.
- Add cutover readiness checker and explicit runbook.

## Implemented

1. Added `workai-*` systemd templates in `deploy/systemd/`:
   - API service
   - ingest/parse/normalize/assess services + timers
   - stale sweeper/cost rollup/verify units/healthcheck services + timers
2. Added secrets contract templates:
   - `deploy/secrets.example/db.env.example`
   - `deploy/secrets.example/api.env.example`
   - `deploy/secrets.example/google_sheets.env.example`
   - `deploy/secrets.example/google_sheets_sources.json.example`
3. Added migration tooling:
   - `scripts/run_parallel_diff.py`
   - `scripts/run_cutover_readiness.py`
4. Added ops internals:
   - `WorkAI/ops/parallel_diff.py`
   - `WorkAI/ops/cutover_readiness.py`
5. Added cutover procedure doc:
   - `CUTOVER.md`
6. Added tests:
   - `tests/unit/test_ops_parallel_diff.py`
   - `tests/unit/test_phase11_systemd_templates.py`

## Decisions

- Canonical production path set to `/opt/workai`.
- Transitional `/opt/WorkAI` is explicitly documented as temporary during migration.
- Phase 11 readiness result intentionally returns `risky` until real 7-day parallel
  run and post-cutover hold are executed.

## Validation

Validation commands are executed in this iteration:

- `ruff check .`
- `mypy WorkAI`
- `pytest`

## Open items before true DONE

- Real 7-day parallel run with >=95% alignment.
- Real cutover execution window.
- 24h green healthcheck after cutover.
- Rollback drill with measured <=5 minute objective.
