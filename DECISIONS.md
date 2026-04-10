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

## ADR-0011: Spec-aligned contract fields must be materialized in tasks_normalized

- Status: Accepted
- Date: 2026-04-09
- Context: Assess Step 1 initially used reconstructive logic (derived employee id and inferred field semantics), which violated DB-contract-first architecture.
- Decision: Contract fields required by assess are materialized in `tasks_normalized` and populated by normalize: `raw_task_id`, `task_date`, `employee_id`, `canonical_text`, `task_category`, `time_source`, `is_smart`, `is_micro`, `result_confirmed`, `is_zhdun`.
- Consequences: Assess reads contract columns directly with no hash/equivalence reconstruction; schema migration complexity increases but cross-module behavior becomes explicit and auditable.

## ADR-0012: Aggregation output is persisted in operational_cycles

- Status: Accepted
- Date: 2026-04-09
- Context: Step 3 aggregation must provide deterministic and re-readable output for future audit layer; runtime-only aggregation is not a stable cross-module contract.
- Decision: Persist aggregation result in dedicated table `operational_cycles` with unique key `(employee_id, task_date, cycle_key)`.
- Consequences: Audit and downstream consumers can read stable aggregated cycles from DB; aggregation runner uses deterministic cycle keys and per employee/day refresh semantics to avoid stale rows.

## ADR-0013: Bayesian dynamic norms use centralized MVP baseline priors

- Status: Accepted
- Date: 2026-04-09
- Context: Product baseline prior catalog is not yet fully transferred into repository, but Step 4 requires deterministic priors for Bayesian update.
- Decision: Store temporary baseline priors in `WorkAI.assess.bayesian_norms.BASELINE_PRIORS_MINUTES` as a centralized replaceable mapping.
- Consequences: Bayesian updates are deterministic and transparent now; priors can be swapped later without changing DB contract or runner API.

## ADR-0014: Knowledge base uses soft-sync indexing + explicit cache clear

- Status: Accepted
- Date: 2026-04-09
- Context: Phase 6 needs idempotent markdown indexing and fast lookup without introducing operationally risky deletions or external search infrastructure.
- Decision:
  - persist methodology corpus in `knowledge_base_articles`;
  - index with UPSERT by `source_path`;
  - use soft-sync in MVP (do not auto-delete rows for missing files);
  - use lookup LRU cache (`maxsize=100`) by `(query, limit)` and clear cache after index run.
- Consequences: predictable reruns and safe first rollout; stale rows from deleted files may remain until future cleanup policy/full-sync mode is introduced.

## ADR-0015: Audit run cache semantics via completed and completed_cached ledger rows

- Status: Accepted
- Date: 2026-04-09
- Context: Phase 7 requires idempotent `run_audit(employee_id, task_date, force=False)` while preserving observability of cache hits.
- Decision:
  - keep latest real execution as `completed`;
  - on non-force cache hit, persist a new `completed_cached` row carrying reused report payload;
  - on `force=true`, always create a new `processing -> completed/failed` run.
- Consequences: full run history remains explicit and queryable; repeated cached calls increase ledger row count by design.

## ADR-0016: Audit prefetch and tool usage boundaries

- Status: Accepted
- Date: 2026-04-09
- Context: Crew tasks must not repeatedly fetch the same operational data and should only call methodology lookup when needed.
- Decision:
  - prefetch operational cycles and assess metrics once before Crew kickoff and pass through `inputs`;
  - reporter-only `MethodologyLookupTool` is enabled conditionally when `ghost_time_hours >= 4.0`.
- Consequences: deterministic, lower-overhead audit runs and reduced duplicate I/O during sequential agent execution.

## ADR-0017: Phase 11 re-scoped from v1 migration to v2-first safe launch

- Status: Accepted
- Date: 2026-04-10
- Context: Original Phase 11 required 7-day v1/v2 parallel run, >=95% alignment to v1, and rollback to working v1. In current project state, v1 is not a stable production baseline.
- Decision:
  - waive v1-dependent acceptance gates;
  - redefine Phase 11 as safe production launch enablement for v2;
  - use v2-centric readiness checks (health/smoke, deploy artifacts, rollback to previous deploy/snapshot).
- Consequences:
  - migration criteria are explicit and realistic for current operations;
  - historical parity with v1 is no longer a release gate;
  - stronger emphasis on backup/restore discipline and launch observation window.

## ADR-0018: Phase 12 hardened Ruff profile uses focused risk categories

- Status: Accepted
- Date: 2026-04-10
- Context: Full `ruff --select ALL` produces high noise for this mature codebase (docstring/test-style/legacy exceptions), reducing hardening signal quality.
- Decision:
  - keep baseline `ruff check .` as mandatory quality gate;
  - add Phase 12 hardened profile targeting risk-heavy categories:
    - `TRY`, `BLE`, `S`, `DTZ`, `PERF`;
  - ignore subset of known noisy/non-actionable rules (documented in runbook and hardening script).
- Consequences:
  - static analysis focuses on reliability/security/perf risks with actionable signal;
  - strictness is increased without introducing broad suppression in default developer loop.

## ADR-0019: Freeze v2 production-like baseline from live sheets

- Status: Accepted
- Date: 2026-04-10
- Context: WorkAI v2 reached stable end-to-end execution on connected Google Sheets and needs a fixed operational baseline before further hardening.
- Decision:
  - record baseline runtime assumptions (`/opt/workai -> /opt/WorkAI`, `Itogmain`);
  - record observed pipeline counters as baseline snapshot;
  - treat weekly-board parse support as part of baseline parser behavior.
- Consequences:
  - team has a concrete reference point for regression checks;
  - future changes can be evaluated against a known live-data baseline.

## ADR-0020: Audit force-path failure persistence must survive mid-run pool closure

- Status: Accepted
- Date: 2026-04-10
- Context: `run_audit --force` could hit an exception after an inner tool call closed the shared DB pool, then fail again while writing `failed` status (`DatabaseError` masking original exception).
- Decision:
  - stop closing the global DB pool inside knowledge-base lookup calls used by audit tools;
  - harden `run_audit` failure persistence with one re-init attempt before writing failed status.
- Consequences:
  - force-path no longer masks primary errors with pool lifecycle exceptions;
  - failed-run observability in `audit_runs` is preserved even when pool closure happens mid-run.

## ADR-0021: Server integration tests must run on isolated database

- Status: Accepted
- Date: 2026-04-10
- Context: Running `pytest -m integration` against runtime DB causes flaky results due to existing production-like state.
- Decision:
  - keep runtime DB in `/etc/workai/secrets/db.env` (`workai_v2_test`);
  - use dedicated integration DB via `/etc/workai/secrets/db.test.env` (`workai_v2_integration`);
  - require integration smoke to load `db.test.env` explicitly.
- Consequences:
  - integration smoke is deterministic and does not mutate runtime production-like state;
  - operational runtime remains isolated from test churn.

## ADR-0022: Final project dossier as canonical operational summary

- Status: Accepted
- Date: 2026-04-10
- Context: Project reached full phase completion and needed one authoritative, consolidated operational document.
- Decision:
  - maintain `docs/FINAL_PROJECT_DOSSIER.md` as canonical final summary of architecture, runtime, contracts, operations, and accepted risks;
  - keep core docs (`README`, `RUNBOOK`, `ROADMAP`, `TASK_BOARD`, `ARCHITECTURE`) synchronized with the dossier.
- Consequences:
  - onboarding and audits get one source of truth for real project state;
  - contradictions across distributed docs are reduced.
