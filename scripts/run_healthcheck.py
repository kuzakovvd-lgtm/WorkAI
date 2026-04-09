"""CLI entrypoint for ops healthcheck."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI healthcheck runner")
    parser.add_argument("--date", dest="target_date", default=None, help="Target date YYYY-MM-DD")
    parser.add_argument("--unit-dir", dest="unit_dir", default="/etc/systemd/system")
    return parser


def main() -> int:
    from WorkAI.ops.healthcheck import healthcheck_exit_code, healthcheck_to_dict, run_healthcheck

    args = _build_parser().parse_args()
    target_date = None if args.target_date is None else date.fromisoformat(args.target_date)

    result = run_healthcheck(target_date=target_date, unit_dir=args.unit_dir)
    print(json.dumps(healthcheck_to_dict(result), ensure_ascii=False, indent=2))
    return healthcheck_exit_code(result.severity)


if __name__ == "__main__":
    raise SystemExit(main())
