# Phase 8 Iteration Log — API (FastAPI)

Date: 2026-04-09
Status: In progress
Scope: HTTP API layer over parse/normalize/assess/knowledge/audit contracts.

## Implemented

- Added FastAPI app wiring with lifespan (`init_db`/`close_db`) and global `X-WorkAI-Version` header.
- Added auth dependency with `X-API-Key` policy for all protected endpoints.
- Implemented routers:
  - `/health`, `/health/deep`
  - `/tasks/raw`, `/tasks/normalized`, `/tasks/aggregated`
  - `/analysis/start`, `/analysis/status/{run_id}`, `/analysis/history`, `/analysis/{run_id}/feedback`
  - `/team/overview`
  - `/debug/logs`, `/debug/cost`
- Added unified error JSON format handlers.
- Added API SQL helper layer (`WorkAI/api/queries.py`) and DTO schemas (`WorkAI/api/schemas.py`).
- Added API runner script: `scripts/workai_api.py`.
- Added tests:
  - unit: `tests/unit/test_api_http.py`
  - integration: `tests/integration/test_api_smoke.py`

## Config & Dependencies

- Added runtime dependencies: `fastapi`, `uvicorn`.
- Added API settings model and env examples with `WORKAI_API_KEY`.

## Validation (local)

- `ruff check .` — pass
- `mypy WorkAI` — pass
- `pytest -q` — pass
- `pytest -q -m integration` with DSN — pass
- `python -c "from WorkAI.api.main import app"` with required ENV — pass
- `python scripts/workai_api.py --help` — pass

## Notes

- API routes are `async def`.
- Blocking work is wrapped with `asyncio.to_thread(...)`.
- `/health` is intentionally unauthenticated; all other routes require `X-API-Key`.
