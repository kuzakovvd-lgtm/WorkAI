# Phase 10 — Operations (healthcheck, sweeper, rollup, verify_units)

## Scope

- Add `ops` runtime modules for deterministic operational checks and routines.
- Provide CLI entrypoints for each operation.
- Keep behavior DB-driven and JSON-output friendly.

## Implemented

- `WorkAI/ops/healthcheck.py`
- `WorkAI/ops/stale_sweeper.py`
- `WorkAI/ops/cost_rollup.py`
- `WorkAI/ops/verify_units.py`
- `WorkAI/ops/models.py`
- `WorkAI/ops/queries.py`
- Ops scripts:
  - `scripts/run_healthcheck.py`
  - `scripts/run_stale_sweeper.py`
  - `scripts/run_cost_rollup.py`
  - `scripts/run_verify_units.py`
- Tests:
  - unit: healthcheck/cost/verify_units/sweeper helpers
  - integration: `test_ops_smoke.py`

## Notes

- Healthcheck emits severity and per-check details, with exit code mapping 0/1/2 in CLI.
- Sweeper currently covers `audit_runs` stale processing rows (`>15m`).
- Cost rollup aggregates from `audit_runs.report_json._usage` and upserts `audit_cost_daily`.
- `verify_units` parses `ExecStart` from `workai-*.service` files and validates interpreter/script paths.
