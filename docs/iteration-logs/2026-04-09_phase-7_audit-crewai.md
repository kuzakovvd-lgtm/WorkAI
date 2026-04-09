# Phase 7 — AI Audit (CrewAI) (2026-04-09)

## Scope

Implement audit MVP with sequential CrewAI orchestration:

- DB contracts: `audit_runs`, `audit_feedback`, `audit_cost_daily`.
- 3-agent sequential flow (analyst -> forensic -> reporter).
- Idempotent `run_audit(employee_id, task_date, force=False)`.
- Cache/force semantics and `_usage` telemetry persistence.
- Audit CLI entrypoint.
- Unit and integration tests with fake crew responses (no real OpenAI calls in CI).

## Key decisions

- Cache hit behavior uses explicit `completed_cached` ledger rows.
- Prefetch occurs once per run from `operational_cycles` + assess metrics.
- Methodology lookup tool enabled only for high ghost-time (`>= 4h`) cases.

## Files changed

- `migrations/versions/0013_audit_tables.py`
- `WorkAI/audit/__init__.py`
- `WorkAI/audit/models.py`
- `WorkAI/audit/schemas.py`
- `WorkAI/audit/agents.py`
- `WorkAI/audit/tasks.py`
- `WorkAI/audit/tools.py`
- `WorkAI/audit/queries.py`
- `WorkAI/audit/crew.py`
- `scripts/run_audit.py`
- `tests/unit/test_audit_settings.py`
- `tests/unit/test_audit_schemas.py`
- `tests/unit/test_audit_tools.py`
- `tests/unit/test_audit_usage.py`
- `tests/integration/test_audit_smoke.py`
- config/docs updates (`settings`, env examples, README/RUNBOOK/DB_CONTRACT/ROADMAP/TASK_BOARD/DECISIONS, iteration index)

## Validation plan

- `ruff check .`
- `mypy WorkAI`
- `pytest`
- `pytest -m integration` (with PostgreSQL)
- `alembic upgrade head --sql`

## Notes

- TODO(TZ §7.4): align agent prompts and final report policy with full external product spec once available.
- TODO(TZ §7.9): implement `audit_cost_daily` rollup job in ops phase.
