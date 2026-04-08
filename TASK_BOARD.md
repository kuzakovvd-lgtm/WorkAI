# WorkAI Task Board

Status date: 2026-04-08

Policy: every non-trivial iteration must update this board together with
`docs/iteration-logs/` entry.

## Done

- [x] Phase 0 bootstrap.
- [x] Phase 1 core infrastructure.
- [x] Phase 2 ingest layer (`Google Sheets -> sheet_cells`).

## In progress

- [ ] Phase 3 parse layer design and `raw_tasks` contract.

## Next

- [ ] Define `raw_tasks` schema and migration(s) for parse layer.
- [ ] Implement parse module entrypoint(s) in `scripts/`.
- [ ] Add parse unit/integration tests.
- [ ] Extend runbook with parse operational checks.

## Backlog

- [ ] Parse layer (Phase 3).
- [ ] Normalize layer (Phase 4).
- [ ] Assess layer (Phase 5).
- [ ] Knowledge base (Phase 6).
- [ ] Audit orchestration (Phase 7).
- [ ] API + notifier + ops (Phases 8-10).
