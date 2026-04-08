# Architectural Decisions (ADR Log)

This file stores short ADR-style entries.

## ADR-0001: Capitalized package name `WorkAI`

- Status: Accepted
- Date: 2026-04-08
- Context: Project contract requires package path `WorkAI/...`.
- Decision: Keep package name as `WorkAI` despite naming-lint conflict.
- Consequences: Ruff ignores `N999`; import paths stay stable against product docs.

## ADR-0002: Module contract is database schema

- Status: Accepted
- Date: 2026-04-08
- Context: Need independent evolution of pipeline layers.
- Decision: Inter-module contract is DB schema and migration history, not Python interfaces.
- Consequences: Strong migration discipline; lower coupling between ingest/parse/normalize/assess/audit.

## ADR-0003: No DB side effects on import

- Status: Accepted
- Date: 2026-04-08
- Context: CI and tooling must run without live DB.
- Decision: DB pool initializes only via explicit `init_db()`.
- Consequences: Predictable imports/tests; runtime startup must call init explicitly.

## ADR-0004: Empty Alembic baseline in Phase 1

- Status: Accepted
- Date: 2026-04-08
- Context: Full business schema was not in repository scope during Phase 1.
- Decision: Create `0001_baseline` without domain DDL.
- Consequences: Migration chain established; schema DDL starts in following phases.

## ADR-0005: Parse idempotency uses full-refresh per sheet

- Status: Accepted
- Date: 2026-04-08
- Context: Parse must be deterministic and safe for repeated runs without duplicate `raw_tasks`.
- Decision: For each `(spreadsheet_id, sheet_title)` parse run deletes existing `raw_tasks` for the sheet and inserts freshly parsed rows.
- Consequences: Stable idempotency with simple semantics; potential extra write load on large sheets (can be optimized later with optional incremental mode).
