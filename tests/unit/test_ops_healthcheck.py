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
