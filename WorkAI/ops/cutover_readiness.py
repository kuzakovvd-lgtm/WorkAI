"""Cutover readiness checks for Phase 11 migration planning."""

from __future__ import annotations

import configparser
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from WorkAI.ops.models import CheckResult, CutoverReadinessResult

_CANONICAL_PATH = "/opt/workai"
_CURRENT_PATH = "/opt/WorkAI"

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

    residual_risks.extend(
        [
            "Parallel run for 7 full calendar days is not completed inside repository checks.",
            "24h post-cutover health hold period must be confirmed in production runtime.",
            "Rollback <= 5 minutes must be time-tested on target host during rehearsal.",
        ]
    )

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
