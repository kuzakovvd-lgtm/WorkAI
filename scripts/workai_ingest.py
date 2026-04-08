"""CLI entrypoint for ingest runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI ingest runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run", help="Run Google Sheets -> sheet_cells ingest")
    return parser


def main() -> int:
    from WorkAI.ingest import run_ingest

    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        run_ingest()
        return 0

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
