# WorkAI v2 Launch Plan (Phase 11)

Status: **Completed under re-scoped Phase 11 model**.

## Decision

Phase 11 is re-scoped from "migration from working v1 to v2" to
**"safe production launch of v2"**.

## Reason

- Original criteria depended on v1 being a stable production baseline.
- In reality, v1 is not a dependable baseline for quality alignment.
- Rollback to v1 does not provide reliable operational safety.

## Removed original requirements (waived by project decision)

- mandatory 7-day parallel run against v1;
- mandatory `>=95%` alignment with v1 outputs;
- rollback target tied to "working v1 runtime".

## Accepted risks

- launch quality is validated by v2-centric health/smoke gates, not v1 comparison;
- rollback assurance relies on deployment/version control and DB snapshot discipline;
- historical v1 parity metrics are no longer a release gate.

## New acceptance criteria (Phase 11)

1. Deployment contract for v2 is ready:
   - canonical path policy is documented;
   - `workai-*` systemd units/timers exist and validate.
2. Secrets/env contract is ready (`/etc/workai/secrets/*` templates documented).
3. Cutover procedure is documented and executable.
4. Post-launch healthcheck stays green for defined observation window.
5. Post-launch smoke checks pass for key pipelines.
6. Restore/rollback path is documented and drill-ready:
   - rollback to previous deploy/commit;
   - restore via DB snapshot/backup if needed.

## Path policy

- Canonical v2 production path: `/opt/workai`
- Transitional path that may exist in some environments: `/opt/WorkAI`
- v1 path (do not modify in Phase 11 docs/process): `/opt/employee-analytics`

## Preconditions before launch

1. `workai-*` unit/timer templates are installed and `daemon-reload` succeeds.
2. Secrets files exist:
   - `/etc/workai/secrets/db.env`
   - `/etc/workai/secrets/workai.env`
   - `/etc/workai/secrets/api.env`
   - `/etc/workai/secrets/google_sheets.env`
3. `alembic upgrade head` succeeds in v2 environment.
4. Phase 10 healthcheck and smoke scripts pass in launch environment.

## Launch steps

1. Freeze change window and notify stakeholders.
2. Confirm latest DB backup/snapshot.
3. Enable/start v2 timers and services:
   - `workai-cell-ingest.timer`
   - `workai-parse.timer`
   - `workai-normalize.timer`
   - `workai-assess.timer`
   - `workai-stale-sweeper.timer`
   - `workai-cost-rollup.timer`
   - `workai-verify-units.timer`
   - `workai-healthcheck.timer`
   - `workai-api.service`
4. Switch API routing/load-balancer to v2 API endpoint.
5. Run post-launch checks:
   - `python scripts/run_healthcheck.py`
   - key API smoke (`/health`, `/health/deep`, `/analysis/history`)
   - key pipeline smoke scripts.

## Observation window

- Monitor healthcheck severity, pipeline failures, and notification alerts.
- Keep launch in "observation" until configured window is green.

## Rollback strategy (v2-first)

Rollback target is **previous known-good v2 deploy**, not v1.

1. Switch API routing to previous v2 endpoint/revision.
2. Disable current faulty v2 timers/services.
3. Deploy previous known-good commit/tag.
4. If data-level incident exists, restore from validated DB snapshot.
5. Re-run healthcheck and smoke scripts.

## Notes

- This runbook is intentionally non-destructive.
- Legacy v1 runtime was removed during v2-first launch cleanup; rollback target remains previous v2 deploy + DB snapshot.
