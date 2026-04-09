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

## ADR-0006: Normalize idempotency uses full-refresh per sheet/date

- Status: Accepted
- Date: 2026-04-08
- Context: Normalize must produce deterministic `tasks_normalized` rows despite `raw_tasks` being recreated by parse full-refresh.
- Decision: For each `(spreadsheet_id, sheet_title, work_date)` normalize run deletes existing `tasks_normalized` rows for the sheet/date and inserts freshly normalized rows.
- Consequences: Strong idempotency and predictable results; higher write volume on large sheets is accepted in MVP.

## ADR-0007: Employee mapping strategy uses alias map + optional fuzzy fallback

- Status: Accepted
- Date: 2026-04-08
- Context: Source employee names may contain variants/aliases/typos; downstream assess requires stable canonical employee keys.
- Decision: Resolve names with deterministic pipeline: exact canonical match -> alias map -> optional fuzzy (`difflib`) -> fallback to normalized raw name.
- Consequences: Works without extra runtime dependencies; fuzzy quality is basic in MVP and can be upgraded later (e.g., RapidFuzz) without contract changes.

## ADR-0008: Normalize single-flight safety via PostgreSQL advisory locks

- Status: Accepted
- Date: 2026-04-09
- Context: Full-refresh writes are vulnerable to race conditions when concurrent normalize runs target the same sheet/date.
- Decision: Before normalize write for one `(spreadsheet_id, sheet_title, work_date)` partition, runner attempts `pg_try_advisory_lock(hashtextextended(lock_key, 0))` with lock key `normalize|<spreadsheet_id>:<sheet_title>|<work_date>`.
- Consequences: Concurrent conflicting runs become predictable (lock holder proceeds, others skip with structured log); no data corruption from overlapping full-refresh writes. Phase 4.5 policy keeps no retry in-run; repeated skip incidents are handled operationally by rerun/escalation.

## ADR-0009: Record-level normalize failures are persisted in pipeline_errors

- Status: Accepted
- Date: 2026-04-09
- Context: Without DLQ-style persistence, row-level failures are visible only in logs and hard to reprocess.
- Decision: Normalize stores record-level failures into `pipeline_errors` with `run_id`, `source_ref`, `error_type`, bounded `error_message`, and optional payload excerpt; processing aborts sheet/date when `max_errors_per_sheet` is exceeded.
- Consequences: Better incident triage and replayability, with bounded storage and deduplication on `(phase, source_ref, error_hash)`.

## ADR-0010: Pipeline errors retention policy (MVP)

- Status: Accepted
- Date: 2026-04-09
- Context: `pipeline_errors` can grow unbounded under persistent data-quality issues.
- Decision: Apply 90-day retention with weekly manual cleanup batches; automate cleanup in Phase 10 ops.
- Consequences: Controlled table growth before ops module exists; temporary manual maintenance requirement.
