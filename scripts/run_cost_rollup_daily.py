"""Run ops cost rollup for the current date (used by systemd timer)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    from WorkAI.ops.cost_rollup import cost_rollup_to_dict, run_cost_rollup

    parser = argparse.ArgumentParser(description="Run WorkAI cost rollup for one day (default: today)")
    parser.add_argument("--date", dest="rollup_date", default=None, help="Rollup date YYYY-MM-DD")
    args = parser.parse_args()

    rollup_date = date.today() if args.rollup_date is None else date.fromisoformat(args.rollup_date)
    result = run_cost_rollup(rollup_date)
    print(json.dumps(cost_rollup_to_dict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
