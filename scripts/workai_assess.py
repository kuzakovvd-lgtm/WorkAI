"""CLI entrypoint for assess steps."""

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

    run_parser = subparsers.add_parser("run", help="Run assess step1(ghost_time) + step2(scoring)")
    run_parser.add_argument("--date", dest="target_date", required=True, type=_parse_date)

    ghost_parser = subparsers.add_parser("run-ghost-time", help="Run only assess step1 ghost_time")
    ghost_parser.add_argument("--date", dest="target_date", required=True, type=_parse_date)

    scoring_parser = subparsers.add_parser("run-scoring", help="Run only assess step2 scoring")
    scoring_parser.add_argument("--date", dest="target_date", required=True, type=_parse_date)

    return parser


def main() -> int:
    from WorkAI.assess import run_assess, run_assess_ghost_time, run_assess_scoring
    from WorkAI.common import get_logger

    parser = _build_parser()
    args = parser.parse_args()
    logger = get_logger(__name__)

    try:
        if args.command == "run":
            result = run_assess(args.target_date)
            logger.info(
                "assess_cli_done",
                target_date=result.target_date.isoformat(),
                ghost_rows_upserted=result.ghost_time.rows_upserted,
                scoring_rows_upserted=result.scoring.rows_upserted,
            )
            return 0

        if args.command == "run-ghost-time":
            result = run_assess_ghost_time(args.target_date)
            logger.info(
                "assess_cli_ghost_done",
                target_date=result.target_date.isoformat(),
                rows_upserted=result.rows_upserted,
            )
            return 0

        if args.command == "run-scoring":
            result = run_assess_scoring(args.target_date)
            logger.info(
                "assess_cli_scoring_done",
                target_date=result.target_date.isoformat(),
                rows_upserted=result.rows_upserted,
            )
            return 0
    except Exception:
        logger.exception("assess_cli_failed", command=args.command, target_date=args.target_date.isoformat())
        return 1

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
