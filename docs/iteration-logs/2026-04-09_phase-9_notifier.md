# Phase 9 — Notifier (Telegram + notification_log)

## Scope

- Add notifier DB contract table `notification_log`.
- Implement Telegram notifier with severity routing and resilient failure handling.
- Ensure every send attempt is persisted in DB (`delivered=true/false`).
- Add pure rule helpers for future Ops phase decisions.
- Add smoke CLI and unit/integration tests without real Telegram calls in CI.

## Implementation

- Migration `0014_notification_log` created.
- New notifier modules:
  - `models.py`
  - `queries.py`
  - `rules.py`
  - `telegram_bot.py`
- CLI:
  - `scripts/run_notifier_smoke.py`.
- Config:
  - Added `NotifierSettings` with Telegram env aliases.

## Validation

Planned commands for this iteration:

```bash
ruff check .
mypy WorkAI
pytest
WORKAI_DB__DSN=postgresql://postgres:postgres@localhost:5432/postgres pytest -q -m integration
```

## Notes

- CI-safe behavior: tests use mocked transport; no real Telegram network calls.
- `info` level uses admin fallback when dedicated info chat is not configured.
