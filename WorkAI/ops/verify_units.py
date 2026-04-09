"""Systemd unit ExecStart path verification helpers."""

from __future__ import annotations

import glob
import os
import shlex
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Literal

from WorkAI.common import get_logger
from WorkAI.ops.models import Severity, UnitCheckResult, VerifyUnitsResult

_LOG = get_logger(__name__)


def run_verify_units(unit_dir: str = "/etc/systemd/system") -> VerifyUnitsResult:
    """Parse workai-*.service files and validate ExecStart paths."""

    unit_paths = sorted(glob.glob(os.path.join(unit_dir, "workai-*.service")))
    checks: list[UnitCheckResult] = []

    for unit_path in unit_paths:
        unit_name = os.path.basename(unit_path)
        execstart = _extract_execstart(unit_path)
        interpreter_path, script_path = _extract_paths(execstart)

        interpreter_exists = False if interpreter_path is None else os.path.exists(interpreter_path)
        script_exists = False if script_path is None else os.path.exists(script_path)

        status: Literal["ok", "warning", "critical"]
        if execstart == "" or interpreter_path is None or script_path is None:
            status = "warning"
        elif interpreter_exists and script_exists:
            status = "ok"
        else:
            status = "critical"

        checks.append(
            UnitCheckResult(
                unit_name=unit_name,
                execstart=execstart,
                interpreter_path=interpreter_path,
                script_path=script_path,
                interpreter_exists=interpreter_exists,
                script_exists=script_exists,
                status=status,
            )
        )

    severity: Severity
    if not checks:
        severity = "data_warning"
    elif any(item.status == "critical" for item in checks):
        severity = "infra_critical"
    elif any(item.status == "warning" for item in checks):
        severity = "data_warning"
    else:
        severity = "info"

    result = VerifyUnitsResult(
        unit_dir=unit_dir,
        units_checked=len(checks),
        units=checks,
        severity=severity,
        generated_at=datetime.now(UTC),
    )

    _LOG.info(
        "verify_units_completed",
        unit_dir=unit_dir,
        units_checked=result.units_checked,
        severity=result.severity,
    )
    return result


def verify_units_to_dict(result: VerifyUnitsResult) -> dict[str, object]:
    """Serialize verify-units result for CLI JSON output."""

    return {
        "unit_dir": result.unit_dir,
        "units_checked": result.units_checked,
        "severity": result.severity,
        "generated_at": result.generated_at.isoformat(),
        "units": [asdict(item) for item in result.units],
    }


def _extract_execstart(unit_path: str) -> str:
    try:
        with open(unit_path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return ""

    for raw in lines:
        line = raw.strip()
        if line.startswith("ExecStart="):
            return line[len("ExecStart=") :].strip()
    return ""


def _extract_paths(execstart: str) -> tuple[str | None, str | None]:
    if execstart == "":
        return (None, None)

    try:
        tokens = shlex.split(execstart)
    except ValueError:
        return (None, None)

    if not tokens:
        return (None, None)

    interpreter = tokens[0] if os.path.isabs(tokens[0]) else None

    script: str | None = None
    for token in tokens[1:]:
        if token.endswith(".py") and os.path.isabs(token):
            script = token
            break

    if script is None and len(tokens) > 1 and os.path.isabs(tokens[1]):
        script = tokens[1]

    return (interpreter, script)
