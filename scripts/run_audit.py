"""CLI entrypoint for Phase 7 audit runs."""

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
    parser = argparse.ArgumentParser(description="WorkAI AI audit runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run AI audit for one employee/day")
    run_parser.add_argument("--employee-id", dest="employee_id", type=int, required=True)
    run_parser.add_argument("--date", dest="target_date", type=_parse_date, required=True)
    run_parser.add_argument("--force", action="store_true", default=False)

    return parser


def main() -> int:
    from WorkAI.audit import run_audit
    from WorkAI.common import get_logger

    parser = _build_parser()
    args = parser.parse_args()
    logger = get_logger(__name__)

    if args.command != "run":
        parser.error("Unsupported command")
        return 2

    try:
        result = run_audit(args.employee_id, args.target_date, force=args.force)
        logger.info(
            "audit_cli_completed",
            run_id=str(result.run_id),
            employee_id=result.employee_id,
            task_date=result.task_date.isoformat(),
            status=result.status,
            cached=result.cached,
        )
        return 0
    except Exception:
        logger.exception(
            "audit_cli_failed",
            employee_id=args.employee_id,
            task_date=args.target_date.isoformat(),
            force=args.force,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
