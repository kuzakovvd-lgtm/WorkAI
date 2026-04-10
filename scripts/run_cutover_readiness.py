"""CLI helper for Phase 11 cutover readiness checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI cutover readiness checker")
    parser.add_argument(
        "--repo-root",
        dest="repo_root",
        default=str(PROJECT_ROOT),
        help="Repository root path used for artifact checks",
    )
    return parser


def main() -> int:
    from WorkAI.ops.cutover_readiness import cutover_readiness_to_dict, run_cutover_readiness

    args = _build_parser().parse_args()
    result = run_cutover_readiness(repo_root=args.repo_root)
    print(json.dumps(cutover_readiness_to_dict(result), ensure_ascii=False, indent=2))
    if result.status == "ready":
        return 0
    if result.status == "risky":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

