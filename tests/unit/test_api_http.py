from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from WorkAI.audit.models import AuditRunResult
from WorkAI.config import get_settings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("WORKAI_API_KEY", "unit-test-key")
    monkeypatch.setenv("WORKAI_DB__DSN", "postgresql://invalid:invalid@localhost:5432/invalid")
    get_settings.cache_clear()

    from WorkAI.api import dependencies as api_dependencies
    from WorkAI.api import main as api_main

    monkeypatch.setattr(api_main, "init_db", lambda settings: None)
    monkeypatch.setattr(api_main, "close_db", lambda: None)

    api_main.app.dependency_overrides[api_dependencies.get_db] = lambda: None

    with TestClient(api_main.app) as test_client:
        yield test_client

    api_main.app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_health_without_auth_has_version_header(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-WorkAI-Version"] == "2.0.0"
    assert response.json()["status"] == "ok"


def test_protected_route_requires_api_key(client: TestClient) -> None:
    response = client.get("/team/overview", params={"task_date": "2026-04-09"})

    assert response.status_code == 401
    assert response.json() == {"error": {"code": "unauthorized", "message": "Invalid API key"}}


def test_validation_error_shape(client: TestClient) -> None:
    response = client.post(
        "/analysis/start",
        headers={"X-API-Key": "unit-test-key"},
        json={"employee_id": 0, "task_date": "2026-04-09", "force": False},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_analysis_start_serialization(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    run_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    from WorkAI.api.routes import analysis as analysis_routes

    def fake_run_audit(employee_id: int, task_date: date, *, force: bool = False) -> AuditRunResult:
        return AuditRunResult(
            run_id=run_id,
            employee_id=employee_id,
            task_date=task_date,
            status="completed",
            report_json={"executive_summary": "ok"},
            cached=not force,
        )

    monkeypatch.setattr(analysis_routes, "run_audit", fake_run_audit)

    response = client.post(
        "/analysis/start",
        headers={"X-API-Key": "unit-test-key"},
        json={"employee_id": 7, "task_date": "2026-04-09", "force": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(run_id)
    assert body["status"] == "completed"
    assert body["report_json"] == {"executive_summary": "ok"}
