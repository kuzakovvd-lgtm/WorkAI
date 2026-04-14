# WorkAI Runbook

## Current production-like baseline (2026-04-10)

- Runtime path: `/opt/workai`
- Active branch: `Itogmain`
- Connected Google Sheets are ingesting into `sheet_cells`
- Parse fallback for weekly-board layout is enabled and producing `raw_tasks`
- Notifier and healthcheck are operational

Baseline counters:

- `sheet_cells = 31376`
- `raw_tasks = 1892`
- `tasks_normalized = 1892`
- `daily_task_assessments = 39`
- `operational_cycles = 39`
- `audit_runs = 4`

Baseline caveat history:

- Known issue during baseline capture: `run_audit --force` could fail in error-path
  when DB pool was closed by an inner tool call. This issue is tracked and fixed in a
  narrow hotfix (see `DECISIONS.md`).

## Local setup

```bash
./scripts/bootstrap_dev.sh
source .venv/bin/activate
```

Python version policy:

- use Python `3.12.x` only for local, CI and production-like workflows;
- local pin is tracked in `.python-version`;
- package guard is enforced via `requires-python = ">=3.12,<3.13"` in
  `pyproject.toml`.

## Standard verification

```bash
ruff check .
mypy WorkAI
pytest -q -m "not integration and not integration_online"
```

## Emergency server hardening (today)

Apply SSH + fail2ban + firewall hardening and close public `:8000`:

```bash
sudo SSH_PORT=22 PERMIT_ROOT_LOGIN=no scripts/run_server_hardening.sh
```

Optional settings:

- `PERMIT_ROOT_LOGIN=prohibit-password` if root key login must remain available.
- `ALLOW_TCP_PORTS="80 443"` to define additional allowed inbound ports.
- `API_UNIT_PATH=/etc/systemd/system/workai-api.service` if unit path differs.

Post-checks (should pass):

```bash
sudo sshd -T | egrep 'passwordauthentication|permitrootlogin'
sudo fail2ban-client status sshd
sudo ufw status verbose
sudo ss -ltnp | grep ':8000'
```

## Production git-state policy

Repository in `/opt/workai` must stay clean (`git status --short` -> empty).

Rules:

- all deploys are fast-forward to `origin/Itogmain`;
- no direct ad-hoc file edits inside `/opt/workai`;
- runtime artifacts stay outside repo tree (`/var/log`, `/tmp`, `/etc/workai/secrets`);
- if emergency local edits are unavoidable, save patch + promote to PR within 24h.

Quick cleanup:

```bash
cd /opt/workai
git fetch origin
git checkout Itogmain
git reset --hard origin/Itogmain
git clean -fd
git status --short
```

Server integration verification (isolated DB):

```bash
scripts/run_integration_checks.sh

# Online Google integration checks (requires google_sheets.test.env):
WORKAI_PYTEST_MARK_EXPR=integration_online scripts/run_integration_checks.sh
```

## Database environment

Required minimum:

- `WORKAI_DB__DSN`
- `WORKAI_DB__LOCK_TIMEOUT_MS` (default `2000`)

Optional pool tuning:

- `WORKAI_DB__MIN_SIZE`
- `WORKAI_DB__MAX_SIZE`
- `WORKAI_DB__TIMEOUT_SEC`
- `WORKAI_DB__CONNECT_TIMEOUT_SEC`

Server DB split policy:

- production runtime: `/etc/workai/secrets/db.env` -> DB `workai_v2_test`;
- integration smoke: `/etc/workai/secrets/db.test.env` -> DB `workai_v2_integration`;
- integration online (Google): `/etc/workai/secrets/google_sheets.test.env`;
- do not run integration smoke on production runtime DB.

## Migrations

```bash
export WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai
python scripts/workai_migrate.py upgrade head
python scripts/workai_migrate.py current
python scripts/workai_migrate.py downgrade -1
```

Offline SQL generation:

```bash
WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai alembic upgrade head --sql
```

## Connectivity smoke test

```bash
pytest tests/integration/test_db_connectivity.py
```

## Ingest run (Phase 2)

```bash
export WORKAI_GSHEETS__ENABLED=true
export WORKAI_GSHEETS__SPREADSHEET_ID=<spreadsheet-id>
export WORKAI_GSHEETS__RANGES=Sheet1!A1:Z200,Sheet2!A1:Z200
export WORKAI_GSHEETS__SERVICE_ACCOUNT_FILE=/path/to/service-account.json
python scripts/workai_ingest.py run
```

## Parse run (Phase 3)

```bash
export WORKAI_PARSE__ENABLED=true
export WORKAI_GSHEETS__SPREADSHEET_ID=<spreadsheet-id>
export WORKAI_PARSE__HEADER_ROW_IDX=1
export WORKAI_PARSE__EMPLOYEE_COL_IDX=1
export WORKAI_PARSE__DATE_FORMATS=%Y-%m-%d,%d.%m.%Y
python scripts/workai_parse.py run
```

## Normalize run (Phase 4)

```bash
export WORKAI_NORMALIZE__ENABLED=true
export WORKAI_GSHEETS__SPREADSHEET_ID=<spreadsheet-id>
export WORKAI_NORMALIZE__EMPLOYEE_ALIASES_FILE=/path/to/employee-aliases.csv
export WORKAI_NORMALIZE__FUZZY_ENABLED=false
export WORKAI_NORMALIZE__FUZZY_THRESHOLD=90
export WORKAI_NORMALIZE__TIME_PARSE_ENABLED=true
export WORKAI_NORMALIZE__CATEGORY_RULES_FILE=/path/to/category-rules.json
export WORKAI_NORMALIZE__MAX_ERRORS_PER_SHEET=50
python scripts/workai_normalize.py run
```

Normalize concurrency policy:

- Full-refresh is partitioned by `(spreadsheet_id, sheet_title, work_date)`.
- Single-flight is enforced by PostgreSQL advisory lock:
  `normalize|<spreadsheet_id>:<sheet_title>|<work_date>`.
- If lock is not acquired, runner logs `normalize_lock_not_acquired` and skips that partition.
- Skip without retry is intentional in Phase 4.5.
- Operational threshold: if one partition is skipped in more than 3 scheduled runs in a row,
  trigger manual re-run and investigate overlapping scheduler windows or stuck workers.

## Pipeline errors (DLQ-style)

Inspect latest normalize errors:

```bash
psql "$WORKAI_DB__DSN" -c "
SELECT id, run_id, sheet_id, work_date, source_ref, error_type, left(error_message, 120) AS error_message, created_at
FROM pipeline_errors
WHERE phase = 'normalize'
ORDER BY created_at DESC
LIMIT 50;
"
```

Reprocess strategy:

- fix mapping/rules/root cause,
- rerun normalize for the same source spreadsheet/date,
- confirm new run_id has no new `pipeline_errors` rows for affected source_ref values.

Retention policy (MVP):

- keep `pipeline_errors` for 90 days;
- run manual cleanup weekly until ops automation exists;
- move automated cleanup to Phase 10 (ops).

Cleanup SQL (batch):

```bash
psql "$WORKAI_DB__DSN" -c "
DELETE FROM pipeline_errors
WHERE id IN (
  SELECT id
  FROM pipeline_errors
  WHERE created_at < now() - interval '90 days'
  ORDER BY created_at
  LIMIT 5000
);
"
```

## Assess EXPLAIN pre-check

Generate assess-like query plans:

```bash
python scripts/workai_explain_assess.py --date 2026-04-07
python scripts/workai_explain_assess.py --date 2026-04-07 --sheet-id Sheet1
```

Output is written to `docs/perf/assess_explain_<YYYY-MM-DD>.md`.

## Assess run (Phase 5 Step 1)

```bash
python scripts/workai_assess.py run --date 2026-04-07
```

Assess Step 1 reads contract columns directly from `tasks_normalized`:

- `employee_id`
- `task_date`
- `duration_minutes`
- `time_source`
- `result_confirmed`

No assess-side reconstruction is allowed for these fields.

## Knowledge Base run (Phase 6)

Index markdown sources into PostgreSQL:

```bash
python scripts/run_index_knowledge.py run
python scripts/run_index_knowledge.py run --source-dir /tmp/workai-knowledge
```

Lookup example:

```bash
python - <<'PY'
from WorkAI.knowledge_base import lookup_methodology
print(lookup_methodology("ghost time", limit=5))
PY
```

Phase 6 policy:

- source directory default: `/etc/workai/knowledge/sources`;
- sync mode: **soft-sync** (missing files are not auto-deleted from DB);
- lookup uses LRU cache (`maxsize=100`) by `(query, limit)`;
- cache is explicitly cleared after each successful index run.

## Audit run (Phase 7)

Run one employee/day audit:

```bash
export WORKAI_AUDIT__ENABLED=true
export OPENAI_API_KEY=<secret>
export OPENAI_MODEL_ANALYST=gpt-4o-mini
export OPENAI_MODEL_FORENSIC=gpt-4o-mini
export OPENAI_MODEL_REPORTER=gpt-4o
python scripts/run_audit.py run --employee-id 42 --date 2026-04-09
python scripts/run_audit.py run --employee-id 42 --date 2026-04-09 --force
```

Production-safe manual run (same env contract as systemd):

```bash
sudo WORKAI_AUDIT_EMPLOYEE_ID=42 \
  WORKAI_AUDIT_TARGET_DATE=2026-04-09 \
  WORKAI_AUDIT_FORCE=true \
  /opt/workai/scripts/run_audit_prod.sh
```

Required secret for manual/systemd audit run:

```bash
sudo test -f /etc/workai/secrets/openai.env || sudo touch /etc/workai/secrets/openai.env
sudo grep '^OPENAI_API_KEY=' /etc/workai/secrets/openai.env
```

Install reusable systemd manual unit:

```bash
sudo cp deploy/systemd/workai-audit-manual.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl set-environment \
  WORKAI_AUDIT_EMPLOYEE_ID=42 \
  WORKAI_AUDIT_TARGET_DATE=2026-04-09 \
  WORKAI_AUDIT_FORCE=true
sudo systemctl start workai-audit-manual.service
sudo systemctl unset-environment WORKAI_AUDIT_EMPLOYEE_ID WORKAI_AUDIT_TARGET_DATE WORKAI_AUDIT_FORCE
```

Cache/force semantics:

- `force=false`: if `completed` run exists for `(employee_id, task_date)`, runner returns cached report.
- Cached hit is logged as `completed_cached` in `audit_runs`.
- `force=true`: always creates a new `processing -> completed/failed` run.

Audit usage telemetry:

- run writes `_usage` object to `audit_runs.report_json`;
- telemetry extraction is best-effort and must not fail audit run when provider format changes.

## Notifier run (Phase 9)

Run one notifier smoke attempt:

```bash
export WORKAI_DB__DSN=postgresql://user:pass@host:5432/workai
export TELEGRAM_BOT_TOKEN=<secret>
export TELEGRAM_ADMIN_CHAT_ID=<chat-id>
export TELEGRAM_MGMT_CHAT_ID=<chat-id>
python scripts/run_notifier_smoke.py send-test --level info --subject "Notifier smoke" --body "phase-9 check"
```

Notifier policy:

- levels route to channels:
  - `infra_critical` -> admin chat;
  - `data_warning` -> management chat;
  - `info` -> info chat if configured, else admin fallback.
- every attempt writes one row to `notification_log`, including failures.
- Telegram transport failures do not crash caller; result is persisted with `delivered=false`.

Inspect recent notification attempts:

```bash
psql "$WORKAI_DB__DSN" -c "
SELECT id, sent_at, channel, level, subject, delivered, left(coalesce(error, ''), 120) AS error
FROM notification_log
ORDER BY id DESC
LIMIT 50;
"
```

## Operations run (Phase 10)

Healthcheck JSON + exit code mapping:

```bash
python scripts/run_healthcheck.py --unit-dir /etc/systemd/system
echo $?
```

- `0` -> info
- `1` -> data_warning
- `2` -> infra_critical

Stale sweeper:

```bash
python scripts/run_stale_sweeper.py --threshold-minutes 15
```

Cost rollup for one date:

```bash
python scripts/run_cost_rollup.py --date 2026-04-09
```

Verify systemd unit ExecStart paths:

```bash
python scripts/run_verify_units.py --unit-dir /etc/systemd/system
```

Verify timer chain and service outcomes for last 24h (systemctl + journalctl):

```bash
python scripts/run_timer_chain_check.py --window-hours 24
```

## Reverse proxy (nginx) + TLS

Install and enable reverse proxy to local API (`127.0.0.1:8000`):

```bash
sudo /opt/workai/scripts/setup_nginx_reverse_proxy.sh
```

Template path in repository:

- `deploy/nginx/workai.conf`

Issue TLS certificate (public domain required):

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <your-domain>
```

Post-check:

```bash
curl -I http://127.0.0.1:8000/health
curl -I http://<your-domain>/health
curl -I https://<your-domain>/health
```

## Server path conventions

- v2 canonical: `/opt/workai`
- mixed-case path aliases are not allowed in production.
- v1 (do not modify): `/opt/employee-analytics`

## Migration & cutover (Phase 11)

### Decision

Phase 11 is executed as **safe production launch of v2**.

### Reason

Original Phase 11 assumed a working v1 baseline for parallel comparison and rollback.
That assumption is not valid in current project reality, so v1-alignment gates are waived.

### Accepted risks

- no mandatory 7-day v1/v2 parallel run;
- no mandatory `>=95%` alignment versus v1;
- no rollback dependency on v1 runtime.

### New acceptance criteria

- deployment path/unit/secrets contracts are ready;
- cutover/rollback runbook is ready;
- cutover execution evidence is recorded in repository artifacts;
- healthcheck is green for a defined observation window after launch;
- smoke pipeline checks pass post-launch;
- rollback/restore path points to previous deploy + DB snapshot.

### Readiness check

```bash
python scripts/run_cutover_readiness.py
echo $?
```

- `0` -> ready
- `1` -> risky (no blockers, residual risks remain)
- `2` -> blocked

Required evidence file for `ready` status:

- `docs/cutover/cutover_readiness_evidence.json`
- must include and reference artifacts for:
  - path policy alignment (`/opt/workai`);
  - 7-day parallel run completion;
  - >=24h post-cutover hold window;
  - rollback rehearsal <=5 minutes.

Optional post-launch count sanity (v2 snapshots, not v1 baseline):

```bash
python scripts/run_parallel_diff.py \
  --date 2026-04-09 \
  --reference-json /tmp/workai-launch-baseline-counts-2026-04-09.json \
  --tolerance-pct 5
```

Systemd templates:

- located at `deploy/systemd/workai-*.service` and `deploy/systemd/workai-*.timer`
- `ExecStart` points only to `/opt/workai/scripts/*.py`
- secrets are injected via `/etc/workai/secrets/*.env`

Cutover and rollback procedure:

- see `CUTOVER.md` for exact ordered steps, hold period, and rollback sequence.

## Hardening run (Phase 12)

Full hardening checks:

```bash
scripts/run_phase12_hardening_checks.sh
```

Manual split:

```bash
ruff check .
ruff check . --select TRY,BLE,S,DTZ,PERF --ignore BLE001,S101,S105,S108,S310,S311,S324,S608,TRY003,TRY300,TRY301,TRY004,DTZ007,DTZ011,PERF401
mypy WorkAI
WORKAI_DB__DSN=postgresql://postgres:postgres@localhost:5432/postgres pytest -q --cov=WorkAI --cov-report=term --cov-report=xml
```

Performance baseline:

```bash
python scripts/run_phase12_benchmarks.py --rows 200 --cols 40 --sheets 3
```

Generated artifact:

- `docs/perf/phase12_baseline_<YYYY-MM-DD>.md`

Disaster recovery:

- see `docs/DR_PLAN.md` for backup/restore commands and validation checklist.
