"""Cutover readiness checks for Phase 11 migration planning."""

from __future__ import annotations

import configparser
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from WorkAI.ops.models import CheckResult, CutoverReadinessResult

_CANONICAL_PATH = "/opt/workai"
_CURRENT_PATH = "/opt/workai"
_CUTOVER_EVIDENCE_FILE = "docs/cutover/cutover_readiness_evidence.json"

_REQUIRED_SYSTEMD_FILES = [
    "workai-api.service",
    "workai-cell-ingest.service",
    "workai-cell-ingest.timer",
    "workai-parse.service",
    "workai-parse.timer",
    "workai-normalize.service",
    "workai-normalize.timer",
    "workai-assess.service",
    "workai-assess.timer",
    "workai-stale-sweeper.service",
    "workai-stale-sweeper.timer",
    "workai-cost-rollup.service",
    "workai-cost-rollup.timer",
    "workai-verify-units.service",
    "workai-verify-units.timer",
    "workai-healthcheck.service",
    "workai-healthcheck.timer",
]

_REQUIRED_DEPLOY_FILES = [
    "deploy/secrets.example/workai.env.example",
    "deploy/secrets.example/db.env.example",
    "deploy/secrets.example/api.env.example",
    "deploy/secrets.example/google_sheets_sources.json.example",
    "scripts/run_parallel_diff.py",
    "scripts/run_cutover_readiness.py",
    "CUTOVER.md",
]


def run_cutover_readiness(repo_root: str | None = None) -> CutoverReadinessResult:
    """Validate repository artifacts required before Phase 11 cutover execution."""

    root = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()
    checks: list[CheckResult] = []
    blockers: list[str] = []
    residual_risks: list[str] = []

    if _CANONICAL_PATH == _CURRENT_PATH:
        checks.append(
            CheckResult(
                name="path_policy",
                status="ok",
                severity="info",
                message="Canonical and current path are aligned.",
                details={"canonical_path": _CANONICAL_PATH, "current_path": _CURRENT_PATH},
            )
        )
    else:
        checks.append(
            CheckResult(
                name="path_policy",
                status="warning",
                severity="data_warning",
                message="Canonical path differs from current operational path.",
                details={"canonical_path": _CANONICAL_PATH, "current_path": _CURRENT_PATH},
            )
        )
        residual_risks.append("Path alignment `/opt/workai` vs `/opt/WorkAI` still requires cutover action.")

    missing_deploy = [rel for rel in _REQUIRED_DEPLOY_FILES if not (root / rel).exists()]
    if missing_deploy:
        blockers.append("Missing required Phase 11 deploy artifacts.")
        checks.append(
            CheckResult(
                name="deploy_artifacts",
                status="critical",
                severity="infra_critical",
                message="Required deploy files are missing.",
                details={"missing": missing_deploy},
            )
        )
    else:
        checks.append(
            CheckResult(
                name="deploy_artifacts",
                status="ok",
                severity="info",
                message="Required deploy files exist.",
                details={"count": len(_REQUIRED_DEPLOY_FILES)},
            )
        )

    systemd_dir = root / "deploy" / "systemd"
    missing_units = [name for name in _REQUIRED_SYSTEMD_FILES if not (systemd_dir / name).exists()]
    if missing_units:
        blockers.append("Missing required `workai-*` unit/timer templates.")
        checks.append(
            CheckResult(
                name="systemd_templates",
                status="critical",
                severity="infra_critical",
                message="Not all required systemd templates exist.",
                details={"missing": missing_units},
            )
        )
    else:
        issues = _validate_systemd_templates(systemd_dir)
        if issues:
            blockers.append("Systemd template policy validation failed.")
            checks.append(
                CheckResult(
                    name="systemd_templates",
                    status="critical",
                    severity="infra_critical",
                    message="Systemd templates contain invalid ExecStart/EnvironmentFile policy.",
                    details={"issues": issues},
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="systemd_templates",
                    status="ok",
                    severity="info",
                    message="Systemd templates satisfy scripts-only and secrets-file policy.",
                    details={"files": len(_REQUIRED_SYSTEMD_FILES)},
                )
            )

    evidence_check, evidence_risks = _validate_cutover_execution_evidence(root)
    checks.append(evidence_check)
    residual_risks.extend(evidence_risks)

    status: Literal["ready", "risky", "blocked"]
    if blockers:
        status = "blocked"
    elif residual_risks:
        status = "risky"
    else:
        status = "ready"

    return CutoverReadinessResult(
        status=status,
        canonical_path=_CANONICAL_PATH,
        current_path=_CURRENT_PATH,
        checks=checks,
        blockers=blockers,
        residual_risks=sorted(set(residual_risks)),
        generated_at=datetime.now(UTC),
    )


def cutover_readiness_to_dict(result: CutoverReadinessResult) -> dict[str, Any]:
    """Serialize cutover readiness result for JSON CLI output."""

    return {
        "status": result.status,
        "canonical_path": result.canonical_path,
        "current_path": result.current_path,
        "generated_at": result.generated_at.isoformat(),
        "blockers": result.blockers,
        "residual_risks": result.residual_risks,
        "checks": [asdict(item) for item in result.checks],
    }


def _validate_systemd_templates(systemd_dir: Path) -> list[str]:
    issues: list[str] = []
    for unit_name in _REQUIRED_SYSTEMD_FILES:
        path = systemd_dir / unit_name
        if unit_name.endswith(".timer"):
            parser = _parse_ini(path)
            timer_unit = parser.get("Timer", "Unit", fallback="")
            if timer_unit == "":
                issues.append(f"{unit_name}: missing Timer.Unit")
            continue

        parser = _parse_ini(path)
        exec_start = parser.get("Service", "ExecStart", fallback="")
        if exec_start == "":
            issues.append(f"{unit_name}: missing Service.ExecStart")
            continue
        if "/opt/workai/scripts/" not in exec_start:
            issues.append(f"{unit_name}: ExecStart must target /opt/workai/scripts/*.py")
        if "/opt/employee-analytics" in exec_start:
            issues.append(f"{unit_name}: ExecStart must not point to v1 paths")

        env_files = parser.get("Service", "EnvironmentFile", fallback="")
        if env_files == "":
            issues.append(f"{unit_name}: missing Service.EnvironmentFile")
        elif "/etc/workai/secrets/" not in env_files:
            issues.append(f"{unit_name}: EnvironmentFile must use /etc/workai/secrets/")
    return issues


def _parse_ini(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str  # type: ignore[assignment]
    content = path.read_text(encoding="utf-8")
    parser.read_string(content)
    return parser


def _validate_cutover_execution_evidence(root: Path) -> tuple[CheckResult, list[str]]:
    evidence_path = root / _CUTOVER_EVIDENCE_FILE
    if not evidence_path.exists():
        return (
            CheckResult(
                name="cutover_execution_evidence",
                status="warning",
                severity="data_warning",
                message="Cutover execution evidence file is missing.",
                details={"path": _CUTOVER_EVIDENCE_FILE},
            ),
            [
                "Path policy alignment is not documented in execution evidence.",
                "Parallel run for 7 full calendar days is not documented in execution evidence.",
                "24h post-cutover hold is not documented in execution evidence.",
                "Rollback rehearsal <= 5 minutes is not documented in execution evidence.",
            ],
        )

    try:
        raw_data = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return (
            CheckResult(
                name="cutover_execution_evidence",
                status="warning",
                severity="data_warning",
                message="Cutover execution evidence file is unreadable.",
                details={"path": _CUTOVER_EVIDENCE_FILE, "error": str(exc)},
            ),
            [
                "Path policy alignment is not documented in execution evidence.",
                "Parallel run for 7 full calendar days is not documented in execution evidence.",
                "24h post-cutover hold is not documented in execution evidence.",
                "Rollback rehearsal <= 5 minutes is not documented in execution evidence.",
            ],
        )

    risks: list[str] = []
    details: dict[str, Any] = {"path": _CUTOVER_EVIDENCE_FILE}

    path_policy = raw_data.get("path_policy", {})
    path_aligned = bool(path_policy.get("aligned"))
    path_artifact = str(path_policy.get("artifact", ""))
    if not path_aligned or not _artifact_exists(root, path_artifact):
        risks.append("Path policy alignment is not documented in execution evidence.")
    details["path_policy"] = {
        "aligned": path_aligned,
        "artifact": path_artifact,
        "artifact_exists": _artifact_exists(root, path_artifact),
    }

    parallel_run = raw_data.get("parallel_run", {})
    parallel_completed = bool(parallel_run.get("completed"))
    parallel_days = int(parallel_run.get("days", 0))
    parallel_artifact = str(parallel_run.get("artifact", ""))
    if not parallel_completed or parallel_days < 7 or not _artifact_exists(root, parallel_artifact):
        risks.append("Parallel run for 7 full calendar days is not documented in execution evidence.")
    details["parallel_run"] = {
        "completed": parallel_completed,
        "days": parallel_days,
        "artifact": parallel_artifact,
        "artifact_exists": _artifact_exists(root, parallel_artifact),
    }

    hold_window = raw_data.get("hold_window", {})
    hold_completed = bool(hold_window.get("completed"))
    hold_hours = float(hold_window.get("hours", 0.0))
    hold_artifact = str(hold_window.get("artifact", ""))
    if not hold_completed or hold_hours < 24.0 or not _artifact_exists(root, hold_artifact):
        risks.append("24h post-cutover hold is not documented in execution evidence.")
    details["hold_window"] = {
        "completed": hold_completed,
        "hours": hold_hours,
        "artifact": hold_artifact,
        "artifact_exists": _artifact_exists(root, hold_artifact),
    }

    rollback = raw_data.get("rollback_rehearsal", {})
    rollback_completed = bool(rollback.get("completed"))
    rollback_minutes = float(rollback.get("duration_minutes", 0.0))
    rollback_artifact = str(rollback.get("artifact", ""))
    if (
        not rollback_completed
        or rollback_minutes <= 0.0
        or rollback_minutes > 5.0
        or not _artifact_exists(root, rollback_artifact)
    ):
        risks.append("Rollback rehearsal <= 5 minutes is not documented in execution evidence.")
    details["rollback_rehearsal"] = {
        "completed": rollback_completed,
        "duration_minutes": rollback_minutes,
        "artifact": rollback_artifact,
        "artifact_exists": _artifact_exists(root, rollback_artifact),
    }

    check_status: Literal["ok", "warning"] = "ok" if not risks else "warning"
    check_message = (
        "Cutover execution evidence confirms path alignment, 7-day parallel run, 24h hold, and rollback rehearsal."
        if not risks
        else "Cutover execution evidence is incomplete."
    )
    return (
        CheckResult(
            name="cutover_execution_evidence",
            status=check_status,
            severity="info" if not risks else "data_warning",
            message=check_message,
            details=details,
        ),
        risks,
    )


def _artifact_exists(root: Path, rel_path: str) -> bool:
    if rel_path == "":
        return False
    return (root / rel_path).exists()
