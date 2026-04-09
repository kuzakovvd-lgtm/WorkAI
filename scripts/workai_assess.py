"""CLI entrypoint for assess ghost-time step."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}', expected YYYY-MM-DD") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkAI assess runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run Step-1 ghost-time assessment")
    run_parser.add_argument("--date", dest="target_date", required=True, type=_parse_date)
    return parser


def main() -> int:
    from WorkAI.assess import run_assess_ghost_time
    from WorkAI.common import get_logger

    parser = _build_parser()
    args = parser.parse_args()
    logger = get_logger(__name__)

    if args.command == "run":
        try:
            result = run_assess_ghost_time(args.target_date)
        except Exception:
            logger.exception("assess_ghost_time_failed", target_date=args.target_date.isoformat())
            return 1

        logger.info(
            "assess_ghost_time_cli_done",
            target_date=result.target_date.isoformat(),
            employees_processed=result.employees_processed,
            rows_upserted=result.rows_upserted,
        )
        return 0

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
