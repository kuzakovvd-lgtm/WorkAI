"""CLI helper for Phase 11 parallel-run count comparison."""

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
    parser = argparse.ArgumentParser(description="WorkAI parallel-run diff helper")
    parser.add_argument("--date", dest="target_date", required=True, help="Target date YYYY-MM-DD")
    parser.add_argument(
        "--reference-json",
        dest="reference_json",
        required=True,
        help="Path to JSON file with v1/reference counts: {\"raw_tasks\": 1, ...}",
    )
    parser.add_argument("--tolerance-pct", dest="tolerance_pct", type=float, default=5.0)
    return parser


def main() -> int:
    from WorkAI.ops.parallel_diff import parallel_diff_to_dict, run_parallel_diff

    args = _build_parser().parse_args()
    target_date = date.fromisoformat(args.target_date)

    with open(args.reference_json, encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise SystemExit("Reference JSON must be object with table->count mapping")
    reference_counts = {str(key): int(value) for key, value in payload.items()}

    result = run_parallel_diff(
        target_date=target_date,
        reference_counts=reference_counts,
        tolerance_pct=args.tolerance_pct,
    )
    rendered = parallel_diff_to_dict(result)
    print(json.dumps(rendered, ensure_ascii=False, indent=2))
    return 0 if not result.violations else 1


if __name__ == "__main__":
    raise SystemExit(main())

