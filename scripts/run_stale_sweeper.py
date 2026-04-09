"""CLI entrypoint for stale sweeper."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI stale sweeper")
    parser.add_argument("--threshold-minutes", type=int, default=15)
    return parser


def main() -> int:
    from WorkAI.ops.stale_sweeper import run_stale_sweeper, stale_sweeper_to_dict

    args = _build_parser().parse_args()
    result = run_stale_sweeper(threshold_minutes=args.threshold_minutes)
    print(json.dumps(stale_sweeper_to_dict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
