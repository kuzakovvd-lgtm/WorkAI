# Phase 12 — Hardening

Date: 2026-04-10
Status: In progress

## Scope

- coverage hardening with integration-enabled run;
- static-analysis hardening profile;
- documentation synchronization;
- reproducible performance baseline tooling;
- disaster recovery documentation.

## Implemented

1. Coverage threshold enforced in `pyproject.toml` (`fail_under = 70`).
2. Added hardening checks script:
   - `scripts/run_phase12_hardening_checks.sh`
3. Added benchmark generator:
   - `scripts/run_phase12_benchmarks.py`
4. Added DR plan:
   - `docs/DR_PLAN.md`
5. Updated docs for Phase 12 status and procedures:
   - README / RUNBOOK / ARCHITECTURE / ROADMAP / TASK_BOARD / DB_CONTRACT / DECISIONS.

## Validation snapshot

- `ruff check .` -> pass
- `mypy WorkAI` -> pass
- `pytest -q` -> pass
- `WORKAI_DB__DSN=... pytest -q --cov=WorkAI ...` -> total coverage `81%`
- `ruff hardened profile` -> pass

## Open items

- push changes and capture green GitHub CI for this hardening pass.
