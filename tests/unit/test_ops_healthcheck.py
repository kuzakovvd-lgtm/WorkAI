from datetime import date

import pytest
from WorkAI.config import Settings
from WorkAI.ops.healthcheck import _aggregate_severity, healthcheck_exit_code
from WorkAI.ops.models import CheckResult


def test_healthcheck_exit_code_mapping() -> None:
    assert healthcheck_exit_code("info") == 0
    assert healthcheck_exit_code("data_warning") == 1
    assert healthcheck_exit_code("infra_critical") == 2


def test_aggregate_severity_prefers_critical() -> None:
    checks = [
        CheckResult(name="a", status="ok", severity="info", message="ok"),
        CheckResult(name="b", status="critical", severity="infra_critical", message="bad"),
    ]
    assert _aggregate_severity(checks) == "infra_critical"


def test_aggregate_severity_warning_path() -> None:
    checks = [
        CheckResult(name="a", status="warning", severity="data_warning", message="warn"),
    ]
    assert _aggregate_severity(checks) == "data_warning"


def test_protected_api_checks_skips_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from WorkAI.ops import healthcheck as module

    monkeypatch.delenv("WORKAI_API_KEY", raising=False)
    settings = Settings.model_validate({})

    checks = module._protected_api_checks(cur=object(), settings=settings)  # type: ignore[arg-type]
    assert checks[0].name == "api_protected_tasks_raw"
    assert checks[0].status == "not_applicable"


def test_protected_api_checks_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from WorkAI.ops import healthcheck as module

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    monkeypatch.setenv("WORKAI_API_KEY", "test-key")
    monkeypatch.setenv("WORKAI_HEALTHCHECK__API_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(module, "fetch_latest_tasks_target", lambda cur: (7, date(2099, 1, 1)))
    monkeypatch.setattr(module, "urlopen", lambda request, timeout=5.0: _Response())

    settings = Settings.model_validate({})
    checks = module._protected_api_checks(cur=object(), settings=settings)  # type: ignore[arg-type]
    assert checks[0].name == "api_protected_tasks_raw"
    assert checks[0].status == "ok"


def test_audit_failed_last_hour_check_critical(monkeypatch: pytest.MonkeyPatch) -> None:
    from WorkAI.ops import healthcheck as module

    monkeypatch.setattr(module, "fetch_audit_failed_last_hour", lambda cur: 1)
    checks = module._audit_failed_last_hour_checks(cur=object())  # type: ignore[arg-type]
    assert checks[0].name == "audit_failed_last_hour"
    assert checks[0].status == "critical"
    assert checks[0].severity == "infra_critical"


def test_result_confirmed_daily_check_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    from WorkAI.ops import healthcheck as module

    monkeypatch.setenv("WORKAI_HEALTHCHECK__RESULT_CONFIRMED_TARGET_PCT", "70")
    monkeypatch.setattr(module, "fetch_result_confirmed_daily", lambda cur, target_date: (10, 6))
    checks = module._result_confirmed_daily_checks(cur=object(), target_date=date(2026, 4, 14))  # type: ignore[arg-type]
    assert checks[0].name == "result_confirmed_daily"
    assert checks[0].status == "warning"
    assert checks[0].severity == "data_warning"
