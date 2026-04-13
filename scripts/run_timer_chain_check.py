"""Check last-24h timer/service execution for ingest -> parse -> normalize -> assess/audit chain."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_CHAIN_SERVICES = [
    "workai-cell-ingest.service",
    "workai-parse.service",
    "workai-normalize.service",
    "workai-assess.service",
]
_CHAIN_TIMERS = [
    "workai-cell-ingest.timer",
    "workai-parse.timer",
    "workai-normalize.timer",
    "workai-assess.timer",
]
_AUX_SERVICES = [
    "workai-stale-sweeper.service",
    "workai-healthcheck.service",
]
_AUX_TIMERS = [
    "workai-stale-sweeper.timer",
    "workai-healthcheck.timer",
]


def _run(args: list[str]) -> str:
    proc = subprocess.run(args, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)} :: {proc.stderr.strip()}")
    return proc.stdout


def _show_properties(unit: str, properties: list[str]) -> dict[str, str]:
    output = _run(["systemctl", "show", unit, "--no-pager", *[f"-p{prop}" for prop in properties]])
    result: dict[str, str] = {}
    for raw in output.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        result[key] = value
    return result


def _usec_to_iso(value: str) -> str | None:
    if value.strip() in {"", "0", "n/a"}:
        return None
    try:
        dt = datetime.fromtimestamp(int(value) / 1_000_000, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None
    return dt.isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check WorkAI systemd timer/service chain for the last 24h")
    parser.add_argument("--window-hours", type=int, default=24, help="Freshness window in hours")
    args = parser.parse_args()

    window_start = datetime.now(UTC) - timedelta(hours=args.window_hours)
    expected_timers = _CHAIN_TIMERS + _AUX_TIMERS
    expected_services = _CHAIN_SERVICES + _AUX_SERVICES

    payload: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "window_hours": args.window_hours,
        "timers": {},
        "services": {},
        "ok": True,
        "issues": [],
    }
    issues = payload["issues"]
    assert isinstance(issues, list)

    list_timers_output = _run(["systemctl", "list-timers", "--all", "--no-pager", "--no-legend"])
    for timer in expected_timers:
        if timer not in list_timers_output:
            issues.append(f"missing timer in systemctl list-timers: {timer}")

    for timer in expected_timers:
        props = _show_properties(timer, ["LastTriggerUSecRealtime", "NextElapseUSecRealtime"])
        last_iso = _usec_to_iso(props.get("LastTriggerUSecRealtime", ""))
        next_iso = _usec_to_iso(props.get("NextElapseUSecRealtime", ""))
        timer_info = {"last_trigger": last_iso, "next_elapse": next_iso}
        cast_timers = payload["timers"]
        assert isinstance(cast_timers, dict)
        cast_timers[timer] = timer_info

        if last_iso is None:
            issues.append(f"{timer}: no LastTrigger timestamp")
            continue

        last_dt = datetime.fromisoformat(last_iso)
        if last_dt < window_start:
            issues.append(
                f"{timer}: last trigger is older than {args.window_hours}h ({last_iso})"
            )

    for service in expected_services:
        props = _show_properties(service, ["Result", "ExecMainStatus", "ActiveState"])
        journal = _run(
            [
                "journalctl",
                "-u",
                service,
                "--since",
                f"{args.window_hours} hours ago",
                "--no-pager",
                "-o",
                "short-iso",
            ]
        )
        service_info = {
            "result": props.get("Result", ""),
            "active_state": props.get("ActiveState", ""),
            "exec_main_status": props.get("ExecMainStatus", ""),
            "journal_lines": len([line for line in journal.splitlines() if line.strip() != ""]),
        }
        cast_services = payload["services"]
        assert isinstance(cast_services, dict)
        cast_services[service] = service_info

        if service_info["journal_lines"] == 0:
            issues.append(f"{service}: no journal entries in the last {args.window_hours}h")
        if "Failed with result" in journal:
            issues.append(f"{service}: journal has failure entries")
        if service_info["result"] not in {"success", ""}:
            issues.append(f"{service}: systemctl Result={service_info['result']}")

    payload["ok"] = len(issues) == 0
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
