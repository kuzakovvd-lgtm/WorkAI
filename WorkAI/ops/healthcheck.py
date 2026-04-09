"""Operational healthcheck runner with severity grading."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from psycopg import Cursor

from WorkAI.common import ConfigError, configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, get_pool, init_db
from WorkAI.ops.models import CheckResult, HealthcheckResult, Severity
from WorkAI.ops.queries import (
    fetch_db_health,
    fetch_recent_audit_failure_rate,
    fetch_table_count,
    fetch_table_max_timestamp,
)
from WorkAI.ops.verify_units import run_verify_units, verify_units_to_dict

_LOG = get_logger(__name__)


def run_healthcheck(
    settings: Settings | None = None,
    *,
    target_date: date | None = None,
    unit_dir: str = "/etc/systemd/system",
) -> HealthcheckResult:
    """Run multi-check healthcheck and return structured severity result."""

    resolved = settings or get_settings()
    configure_logging(resolved)

    checks: list[CheckResult] = []
    today = target_date or date.today()

    # DB/pool checks (infra critical)
    db_ok = False
    pool_ok = False
    try:
        init_db(resolved)
        with connection() as conn, conn.cursor() as cur:
            db_ok = fetch_db_health(cur)
        checks.append(
            CheckResult(
                name="db_reachable",
                status="ok" if db_ok else "critical",
                severity="infra_critical",
                message="Database reachable" if db_ok else "Database health query failed",
            )
        )
    except Exception as exc:
        checks.append(
            CheckResult(
                name="db_reachable",
                status="critical",
                severity="infra_critical",
                message="Database connection failed",
                details={"error": str(exc)},
            )
        )

    try:
        _ = get_pool()
        pool_ok = True
        checks.append(
            CheckResult(
                name="db_pool_usable",
                status="ok",
                severity="infra_critical",
                message="Database pool is initialized",
            )
        )
    except Exception as exc:
        checks.append(
            CheckResult(
                name="db_pool_usable",
                status="critical",
                severity="infra_critical",
                message="Database pool is not initialized",
                details={"error": str(exc)},
            )
        )

    # Data freshness checks
    if db_ok and pool_ok:
        with connection() as conn, conn.cursor() as cur:
            checks.extend(_freshness_checks(cur))
            checks.extend(_data_volume_checks(cur, today))
            checks.extend(_audit_error_rate_checks(cur, today))

    # Unit verification
    verify_result = run_verify_units(unit_dir=unit_dir)
    checks.append(
        CheckResult(
            name="verify_units",
            status="ok" if verify_result.severity == "info" else ("critical" if verify_result.severity == "infra_critical" else "warning"),
            severity=verify_result.severity,
            message="Systemd unit ExecStart paths verified",
            details=verify_units_to_dict(verify_result),
        )
    )

    severity = _aggregate_severity(checks)

    result = HealthcheckResult(
        severity=severity,
        checks=checks,
        generated_at=datetime.now(UTC),
    )

    _LOG.info(
        "healthcheck_completed",
        severity=result.severity,
        checks=len(result.checks),
    )
    close_db()
    return result


def healthcheck_to_dict(result: HealthcheckResult) -> dict[str, object]:
    """Serialize healthcheck result for CLI JSON output."""

    return {
        "severity": result.severity,
        "generated_at": result.generated_at.isoformat(),
        "checks": [
            {
                "name": check.name,
                "status": check.status,
                "severity": check.severity,
                "message": check.message,
                "details": check.details,
            }
            for check in result.checks
        ],
    }


def healthcheck_exit_code(severity: Severity) -> int:
    """Map severity to process exit code."""

    if severity == "info":
        return 0
    if severity == "data_warning":
        return 1
    if severity == "infra_critical":
        return 2
    raise ConfigError(f"Unsupported severity: {severity}")


def _freshness_checks(cur: Cursor[object]) -> list[CheckResult]:
    now = datetime.now(UTC)
    max_age = timedelta(hours=48)
    checks: list[CheckResult] = []

    fresh_targets = [
        ("raw_tasks", "parsed_at"),
        ("tasks_normalized", "normalized_at"),
        ("audit_runs", "started_at"),
    ]

    for table_name, column_name in fresh_targets:
        value = fetch_table_max_timestamp(cur, table_name, column_name)
        if value is None:
            checks.append(
                CheckResult(
                    name=f"freshness_{table_name}",
                    status="not_applicable",
                    severity="info",
                    message=f"No rows in {table_name}",
                )
            )
            continue

        if not isinstance(value, datetime):
            checks.append(
                CheckResult(
                    name=f"freshness_{table_name}",
                    status="unknown",
                    severity="data_warning",
                    message=f"Unexpected timestamp type for {table_name}",
                )
            )
            continue

        age = now - value
        if age <= max_age:
            checks.append(
                CheckResult(
                    name=f"freshness_{table_name}",
                    status="ok",
                    severity="info",
                    message=f"{table_name} freshness is within threshold",
                    details={"max_age_hours": 48, "age_hours": round(age.total_seconds() / 3600, 2)},
                )
            )
        else:
            checks.append(
                CheckResult(
                    name=f"freshness_{table_name}",
                    status="warning",
                    severity="data_warning",
                    message=f"{table_name} data is stale",
                    details={"max_age_hours": 48, "age_hours": round(age.total_seconds() / 3600, 2)},
                )
            )

    return checks


def _data_volume_checks(cur: Cursor[object], target_date: date) -> list[CheckResult]:
    raw_count = fetch_table_count(cur, "raw_tasks")
    normalized_count = fetch_table_count(cur, "tasks_normalized")

    if raw_count == 0 and normalized_count == 0:
        return [
            CheckResult(
                name="data_volume",
                status="not_applicable",
                severity="info",
                message="No raw/normalized data yet",
                details={"raw_tasks": raw_count, "tasks_normalized": normalized_count},
            )
        ]

    if normalized_count == 0 and raw_count > 0:
        return [
            CheckResult(
                name="data_volume",
                status="warning",
                severity="data_warning",
                message="raw_tasks present but tasks_normalized is empty",
                details={"raw_tasks": raw_count, "tasks_normalized": normalized_count},
            )
        ]

    return [
        CheckResult(
            name="data_volume",
            status="ok",
            severity="info",
            message="Data volume checks passed",
            details={"raw_tasks": raw_count, "tasks_normalized": normalized_count, "target_date": target_date.isoformat()},
        )
    ]


def _audit_error_rate_checks(cur: Cursor[object], target_date: date) -> list[CheckResult]:
    failed_runs, total_runs = fetch_recent_audit_failure_rate(cur, target_date)

    if total_runs == 0:
        return [
            CheckResult(
                name="audit_error_rate",
                status="not_applicable",
                severity="info",
                message="No audit runs in the last 7 days",
            )
        ]

    ratio = failed_runs / float(total_runs)
    if failed_runs >= 3 and ratio >= 0.2:
        return [
            CheckResult(
                name="audit_error_rate",
                status="warning",
                severity="data_warning",
                message="Audit failure ratio exceeds threshold",
                details={"failed_runs": failed_runs, "total_runs": total_runs, "failure_ratio": round(ratio, 4)},
            )
        ]

    return [
        CheckResult(
            name="audit_error_rate",
            status="ok",
            severity="info",
            message="Audit failure ratio is acceptable",
            details={"failed_runs": failed_runs, "total_runs": total_runs, "failure_ratio": round(ratio, 4)},
        )
    ]


def _aggregate_severity(checks: list[CheckResult]) -> Severity:
    if any(check.severity == "infra_critical" and check.status == "critical" for check in checks):
        return "infra_critical"
    if any(check.severity == "data_warning" and check.status in {"warning", "critical", "unknown"} for check in checks):
        return "data_warning"
    if any(check.severity == "infra_critical" and check.status == "warning" for check in checks):
        return "data_warning"
    return "info"
