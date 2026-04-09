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

## In progress

- [ ] Phase 6 knowledge base (FTS index + lookup + cache).

## Next

- [ ] Finalize Phase 6 validation in CI and merge.
- [ ] Start Phase 7 audit layer scaffolding against assess + knowledge contracts.
- [ ] Add audit-focused integration smoke tests.

## Backlog

- [ ] Knowledge base (Phase 6).
- [ ] Audit orchestration (Phase 7).
- [ ] API + notifier + ops (Phases 8-10).
