"""Daily audit usage rollup into audit_cost_daily."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from WorkAI.common import configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db
from WorkAI.notifier import should_alert_on_cost_spike
from WorkAI.ops.models import CostRollupResult
from WorkAI.ops.queries import (
    fetch_audit_usage_for_date,
    fetch_recent_cost_history,
    upsert_audit_cost_daily,
)

_LOG = get_logger(__name__)


def run_cost_rollup(
    rollup_date: date,
    settings: Settings | None = None,
) -> CostRollupResult:
    """Aggregate daily usage totals from audit_runs.report_json._usage."""

    resolved = settings or get_settings()
    configure_logging(resolved)
    init_db(resolved)

    runs_seen = 0
    usage_rows_used = 0
    usage_rows_skipped = 0
    input_tokens = 0
    output_tokens = 0
    cost_usd = 0.0
    history: list[float] = []

    try:
        with connection() as conn, conn.cursor() as cur:
            rows = fetch_audit_usage_for_date(cur, rollup_date)
            runs_seen = len(rows)

            for row in rows:
                usage = _extract_usage(row[1])
                if usage is None:
                    usage_rows_skipped += 1
                    continue
                usage_rows_used += 1
                input_tokens += int(usage["input_tokens"])
                output_tokens += int(usage["output_tokens"])
                cost_usd += float(usage["cost_usd"])

            upsert_audit_cost_daily(
                cur,
                rollup_date=rollup_date,
                runs_count=usage_rows_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=round(cost_usd, 4),
            )

            history = fetch_recent_cost_history(cur, rollup_date, limit=7)
            conn.commit()
    finally:
        close_db()

    spike = should_alert_on_cost_spike(today_cost=round(cost_usd, 4), history=history)

    result = CostRollupResult(
        rollup_date=rollup_date,
        runs_seen=runs_seen,
        usage_rows_used=usage_rows_used,
        usage_rows_skipped=usage_rows_skipped,
        runs_count=usage_rows_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost_usd, 4),
        cost_spike_detected=spike,
        finished_at=datetime.now(UTC),
    )

    _LOG.info(
        "cost_rollup_completed",
        rollup_date=rollup_date.isoformat(),
        runs_seen=result.runs_seen,
        usage_rows_used=result.usage_rows_used,
        usage_rows_skipped=result.usage_rows_skipped,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
        cost_spike_detected=result.cost_spike_detected,
    )
    return result


def cost_rollup_to_dict(result: CostRollupResult) -> dict[str, object]:
    """Serialize rollup result for CLI JSON output."""

    return {
        "rollup_date": result.rollup_date.isoformat(),
        "runs_seen": result.runs_seen,
        "usage_rows_used": result.usage_rows_used,
        "usage_rows_skipped": result.usage_rows_skipped,
        "runs_count": result.runs_count,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": result.cost_usd,
        "cost_spike_detected": result.cost_spike_detected,
        "finished_at": result.finished_at.isoformat(),
    }


def _extract_usage(report_json: Any) -> dict[str, int | float] | None:
    if not isinstance(report_json, dict):
        return None

    raw_usage = report_json.get("_usage")
    if not isinstance(raw_usage, dict):
        return None

    input_tokens = _as_int(raw_usage.get("input_tokens"), default=0)
    output_tokens = _as_int(raw_usage.get("output_tokens"), default=0)
    cost_usd = _as_float(raw_usage.get("cost_usd"), default=0.0)

    return {
        "input_tokens": max(0, input_tokens),
        "output_tokens": max(0, output_tokens),
        "cost_usd": max(0.0, cost_usd),
    }


def _as_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
