"""Run assess pipeline for the current date (used by systemd timer)."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    from WorkAI.assess import run_assess
    from WorkAI.common import get_logger

    parser = argparse.ArgumentParser(description="Run WorkAI assess for one day (default: today)")
    parser.add_argument("--date", dest="target_date", default=None, help="Target date YYYY-MM-DD")
    args = parser.parse_args()

    logger = get_logger(__name__)
    target_date = date.today() if args.target_date is None else date.fromisoformat(args.target_date)
    try:
        result = run_assess(target_date)
        logger.info(
            "assess_daily_completed",
            target_date=result.target_date.isoformat(),
            ghost_rows_upserted=result.ghost_time.rows_upserted,
            scoring_rows_upserted=result.scoring.rows_upserted,
            aggregation_cycles_written=result.aggregation.cycles_written,
            bayesian_rows_recomputed=result.bayesian_norms.rows_recomputed,
        )
        return 0
    except Exception:
        logger.exception("assess_daily_failed", target_date=target_date.isoformat())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
