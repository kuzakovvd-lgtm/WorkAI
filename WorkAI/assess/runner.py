"""Assess runner for Phase 5 Step 1: ghost time + base trust."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from WorkAI.assess.ghost_time import calculate_ghost_minutes, calculate_index_of_trust_base
from WorkAI.assess.models import AssessGhostTimeResult, EmployeeDailyGhostTimeRow
from WorkAI.assess.queries import (
    fetch_employee_day_metrics,
    list_employee_day_keys,
    upsert_employee_daily_ghost_time_batch,
)
from WorkAI.common import configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db

_LOG = get_logger(__name__)


def _quantize_trust(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def run_assess_ghost_time(target_date: date, settings: Settings | None = None) -> AssessGhostTimeResult:
    """Run ghost-time assess step for a specific date."""

    resolved = settings or get_settings()
    configure_logging(resolved)
    init_db(resolved)

    rows_to_upsert: list[EmployeeDailyGhostTimeRow] = []

    try:
        with connection() as conn:
            with conn.cursor() as cur:
                keys = list_employee_day_keys(cur, target_date)

                for key in keys:
                    metrics = fetch_employee_day_metrics(cur, key.employee_id, key.task_date)
                    ghost_minutes = calculate_ghost_minutes(metrics.logged_minutes)
                    trust_base = calculate_index_of_trust_base(
                        total_tasks=metrics.total_tasks,
                        none_count=metrics.none_count,
                        unconfirmed_count=metrics.unconfirmed_count,
                    )

                    rows_to_upsert.append(
                        EmployeeDailyGhostTimeRow(
                            employee_id=key.employee_id,
                            task_date=key.task_date,
                            workday_minutes=480,
                            logged_minutes=metrics.logged_minutes,
                            ghost_minutes=ghost_minutes,
                            index_of_trust_base=_quantize_trust(trust_base),
                        )
                    )

                upsert_employee_daily_ghost_time_batch(cur, rows_to_upsert)
            conn.commit()
    finally:
        close_db()

    result = AssessGhostTimeResult(
        target_date=target_date,
        employees_processed=len(rows_to_upsert),
        rows_upserted=len(rows_to_upsert),
    )
    _LOG.info(
        "assess_ghost_time_completed",
        target_date=target_date.isoformat(),
        employees_processed=result.employees_processed,
        rows_upserted=result.rows_upserted,
    )
    return result
