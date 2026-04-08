"""CLI entrypoint for parse runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI parse runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run", help="Run sheet_cells -> raw_tasks parse")
    return parser


def main() -> int:
    from WorkAI.parse import run_parse

    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        run_parse()
        return 0

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
