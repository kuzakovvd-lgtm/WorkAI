from __future__ import annotations

import configparser
from pathlib import Path

from WorkAI.ops.cutover_readiness import run_cutover_readiness


def test_cutover_readiness_has_no_blockers() -> None:
    result = run_cutover_readiness(repo_root=str(Path.cwd()))
    assert result.status == "ready"
    assert result.blockers == []
    assert result.residual_risks == []


def test_systemd_templates_use_scripts_only_execstart() -> None:
    systemd_dir = Path("deploy/systemd")
    service_paths = sorted(systemd_dir.glob("workai-*.service"))
    assert service_paths

    for path in service_paths:
        parser = configparser.ConfigParser(strict=False)
        parser.optionxform = str
        parser.read(path, encoding="utf-8")

        exec_start = parser.get("Service", "ExecStart")
        assert "/opt/workai/scripts/" in exec_start
        assert "/opt/employee-analytics" not in exec_start

        script_token = next(token for token in exec_start.split() if token.startswith("/opt/workai/scripts/"))
        repo_script_path = Path("scripts") / Path(script_token).name
        assert repo_script_path.exists(), f"Missing script for {path.name}: {repo_script_path}"
