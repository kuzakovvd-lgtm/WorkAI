from pathlib import Path

from WorkAI.ops.verify_units import _extract_paths, run_verify_units


def test_extract_paths_from_execstart() -> None:
    interpreter, script = _extract_paths("/usr/bin/python3 /opt/workai/scripts/run_healthcheck.py")
    assert interpreter == "/usr/bin/python3"
    assert script == "/opt/workai/scripts/run_healthcheck.py"


def test_verify_units_detects_missing_paths(tmp_path: Path) -> None:
    unit = tmp_path / "workai-test.service"
    unit.write_text(
        "[Service]\nWorkingDirectory=/opt/workai\nExecStart=/missing/python /missing/script.py\n",
        encoding="utf-8",
    )

    result = run_verify_units(unit_dir=str(tmp_path))
    assert result.units_checked == 1
    assert result.units[0].status == "critical"
    assert result.severity == "infra_critical"


def test_verify_units_detects_legacy_runtime_path(tmp_path: Path) -> None:
    unit = tmp_path / "workai-legacy.service"
    unit.write_text(
        "[Service]\nWorkingDirectory=/opt/WorkAI\nExecStart=/opt/WorkAI/.venv/bin/python /opt/WorkAI/scripts/run_healthcheck.py\n",
        encoding="utf-8",
    )

    result = run_verify_units(unit_dir=str(tmp_path))
    assert result.units_checked == 1
    assert result.units[0].status == "critical"
    assert result.units[0].path_policy_ok is False
