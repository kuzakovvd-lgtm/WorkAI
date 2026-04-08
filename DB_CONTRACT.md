# Database Contract

## Principle

Database schema is the formal contract between modules.

## Dependency contract

- `api`, `ops` may depend on pipeline modules.
- All modules may depend on `db`, `config`, `common`.
- Reverse/circular imports across domain modules are forbidden.

## Current contract state (Phase 1)

- Alembic baseline exists: revision `0001_baseline`.
- Business tables are intentionally not introduced yet.
- Runtime DB access goes through `WorkAI.db` helpers and explicit `init_db()`.

## Invariants

- No module may assume live DB on import.
- Schema changes must be represented by Alembic revisions.
- Backward compatibility of running pipelines must be considered in every migration.
- Any new table used as cross-module contract must be documented here.

## Migration policy

- Every schema change: migration + rationale in `DECISIONS.md` and iteration log.
- Avoid destructive migrations without explicit rollout/rollback plan.
- For lock-sensitive changes, use configured lock timeout and maintenance windows.
