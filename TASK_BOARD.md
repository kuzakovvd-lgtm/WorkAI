# WorkAI Task Board

Status date: 2026-04-09

Policy: every non-trivial iteration must update this board together with
`docs/iteration-logs/` entry.

## Done

- [x] Phase 0 bootstrap.
- [x] Phase 1 core infrastructure.
- [x] Phase 2 ingest layer (`Google Sheets -> sheet_cells`).
- [x] Phase 3 parse layer (`sheet_cells -> raw_tasks`).
- [x] Phase 4 normalize layer (`raw_tasks -> tasks_normalized`).
- [x] Phase 4.5 pre-flight hardening (CI postgres, DLQ, normalize single-flight lock).
- [x] Phase 5 assess layer (ghost time, scoring, aggregation, Bayesian norms).
- [x] Phase 6 knowledge base (markdown index + PostgreSQL FTS lookup + cache).

## In progress

- [ ] Phase 7 AI audit (CrewAI sequential flow + audit_runs).

## Next

- [ ] Finalize Phase 7 validation in CI and merge.
- [ ] Start Phase 8 API layer against assess/audit contracts.
- [ ] Add API-focused integration smoke tests.

## Backlog

- [ ] Audit orchestration (Phase 7).
- [ ] API + notifier + ops (Phases 8-10).
