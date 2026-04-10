# Disaster Recovery Plan (Phase 12)

## Scope

This plan covers PostgreSQL backup/restore for WorkAI v2 and launch-time recovery
to previous deploy revision.

## Preconditions

- Access to DB credentials (`WORKAI_DB__DSN` or equivalent secure secret file).
- Access to backup storage with retention policy.
- Access to deployment repository branch `Itogmain`.

## Backup procedure

1. Create consistent logical backup:

```bash
export WORKAI_DB__DSN='postgresql://user:pass@host:5432/workai'
TS="$(date +%F_%H%M%S)"
pg_dump --format=custom --file "/var/backups/workai_${TS}.dump" "$WORKAI_DB__DSN"
```

2. Store checksum:

```bash
sha256sum "/var/backups/workai_${TS}.dump" > "/var/backups/workai_${TS}.dump.sha256"
```

3. Replicate backup + checksum to remote backup storage.

## Restore procedure (clean target DB)

1. Prepare empty target database:

```bash
createdb workai_restore
```

2. Restore dump:

```bash
pg_restore --clean --if-exists --no-owner --dbname workai_restore "/var/backups/workai_<TS>.dump"
```

3. Run schema head verification:

```bash
WORKAI_DB__DSN='postgresql://user:pass@host:5432/workai_restore' alembic current
WORKAI_DB__DSN='postgresql://user:pass@host:5432/workai_restore' alembic upgrade head
```

## Post-restore validation checklist

- `SELECT COUNT(*)` sanity checks on contract tables:
  - `raw_tasks`
  - `tasks_normalized`
  - `daily_task_assessments`
  - `employee_daily_ghost_time`
  - `operational_cycles`
  - `audit_runs`
- Run healthcheck:

```bash
WORKAI_DB__DSN='postgresql://user:pass@host:5432/workai_restore' python scripts/run_healthcheck.py
```

- Run integration smoke in restored environment:

```bash
WORKAI_DB__DSN='postgresql://user:pass@host:5432/workai_restore' pytest -q -m integration
```

## Rollback strategy (v2-first)

- Application rollback target: previous known-good v2 commit/deploy artifact.
- Data rollback target: latest validated DB snapshot/dump.
- v1 is not used as runtime rollback target in re-scoped Phase 11+.

## Drill readiness

Recommended cadence:

- monthly backup restore drill to non-production environment;
- record:
  - backup creation duration,
  - restore duration,
  - validation duration,
  - incidents and remediation.
