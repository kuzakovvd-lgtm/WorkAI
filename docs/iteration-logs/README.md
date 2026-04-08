# Iteration Logs

Purpose: detailed execution log per iteration/phase, with decisions, commands, validations, and outcomes.

Format rules:
- One file per iteration.
- File name: `YYYY-MM-DD_phase-<id>_<short-topic>.md`.
- Dates in ISO format (`YYYY-MM-DD`).
- Keep latest iteration at top in the index table.
- For each non-trivial iteration, updating this index is required.
- The same iteration must update `TASK_BOARD.md` status.

## Index

| Date | Iteration | Scope | Commit | Status | Log |
|---|---|---|---|---|---|
| 2026-04-08 | Phase 1 | Core infrastructure (config/common/db/alembic baseline) | `566fe8d` | Completed | [2026-04-08_phase-1_core-infrastructure.md](./2026-04-08_phase-1_core-infrastructure.md) |
| 2026-04-08 | Phase 0 | Repository bootstrap | `ed5d726` | Completed | [2026-04-08_phase-0_bootstrap.md](./2026-04-08_phase-0_bootstrap.md) |

## Sections template

Use [TEMPLATE.md](./TEMPLATE.md) for all next iterations.
