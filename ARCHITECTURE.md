# WorkAI Architecture

> Short technical overview. Full product specification is maintained
> separately by the project owner and supersedes this document.

## Data flow

```text
Google Sheets
     |
     v
ingest  -->  sheet_cells
     |
     v
parse  -->  raw_tasks
     |
     v
normalize  -->  tasks_normalized   key layer
     |
     v
assess  -->  daily_task_assessments, employee_daily_ghost_time, dynamic_task_norms
     |
     v
audit (CrewAI)  -->  audit_runs
     |
     |-->  api  (FastAPI)
     |-->  notifier  (Telegram)
     '-->  ops  (healthcheck, sweeper, rollup)
```

## Dependency direction

```text
api, ops  ->  audit, assess, normalize, parse, ingest, knowledge_base, notifier
   all    ->  db, config, common
```

No reverse or circular imports are allowed. Enforcement: manual review +
`ruff` import sort.

## Module contracts

The contract between modules is the **database schema**, not Python
interfaces. This gives independence and testability: the normalize module
doesn't import parse - both talk to PostgreSQL through `db/`.

## Phase roadmap

| Phase | Scope |
|---|---|
| 0  | Bootstrap: repo skeleton, tooling, CI |
| 1  | Core infra: db, config, common, Alembic baseline |
| 2  | Ingest layer |
| 3  | Parse layer |
| 4  | Normalize layer |
| 5  | Assess layer |
| 6  | Knowledge base |
| 7  | Audit (CrewAI) |
| 8  | API (FastAPI) |
| 9  | Notifier (Telegram) |
| 10 | Operations (healthcheck, sweeper, rollup) |
| 11 | Safe production launch of v2 |
| 12 | Hardening (coverage, static analysis, docs, perf, DR) |

Current state: **Phases 0-12 completed** (Phase 11 re-scoped to v2-first launch).

## Runtime baseline (v2-first)

- Canonical runtime path: `/opt/workai` (single canonical path, no mixed-case aliases).
- Active release branch: `Itogmain`.
- Legacy v1 runtime is removed from active server operations.
- DB split for safety:
  - production runtime DB: `workai_v2_test`,
  - integration smoke DB: `workai_v2_integration`.
- Live data contract is populated from connected Google Sheets end-to-end.

Observed baseline counters (2026-04-10):

- `sheet_cells = 31376`
- `raw_tasks = 1892`
- `tasks_normalized = 1892`
- `daily_task_assessments = 39`
- `operational_cycles = 39`
- `audit_runs = 4`

## Parse layout support

Parse keeps strict matrix parsing and includes a deterministic weekly-board fallback for
real sheets where:

- week header is stored as range text (`dd.mm-dd.mm`) in column A;
- employee identity is represented by worksheet title;
- task text is stored in repeated day-column blocks with `Задача` headers.

## Phase 11 Decision

### Decision

Phase 11 is treated as v2-first production launch enablement, not migration from a working v1 baseline.

### Reason

In this project state, v1 is not a stable/authoritative baseline. Therefore,
parallel alignment and rollback criteria tied to v1 are not reliable launch gates.

### Accepted risks

- waived hard requirement for 7-day v1/v2 parallel run;
- waived hard requirement for `>=95%` alignment with v1 outputs;
- waived rollback dependency on v1 runtime.

### New acceptance criteria

- launch readiness artifacts exist (systemd templates, secrets contract, runbook);
- v2 launch health/smoke checks are green for an observation window;
- rollback target is previous deploy/commit + DB snapshot, not v1 runtime.
