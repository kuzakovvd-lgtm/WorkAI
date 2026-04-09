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
| 11 | Migration & cutover from v1 |
| 12 | Hardening (tests, mypy strict, benchmarks) |

Current phase: **6 (Knowledge Base)**.
