"""Ghost-time and base-trust calculations for assess step 1."""

from __future__ import annotations

from datetime import date

from WorkAI.assess.queries import fetch_employee_day_metrics
from WorkAI.db import connection

WORKDAY_MINUTES = 480


def calculate_ghost_minutes(logged_minutes: int, workday_minutes: int = WORKDAY_MINUTES) -> int:
    """Return non-negative ghost minutes for one day."""

    return max(0, workday_minutes - logged_minutes)


def calculate_index_of_trust_base(total_tasks: int, none_count: int, unconfirmed_count: int) -> float:
    """Return base trust index from `none` and unconfirmed ratios."""

    if total_tasks <= 0:
        return 0.0

    none_ratio = none_count / total_tasks
    unconfirmed_ratio = unconfirmed_count / total_tasks
    base = 1.0 - (0.5 * none_ratio) - (0.5 * unconfirmed_ratio)
    return max(0.0, base)


def compute_ghost_time(employee_id: int, target_date: date) -> int:
    """Compute ghost minutes for one employee/day from tasks_normalized."""

    with connection() as conn, conn.cursor() as cur:
        metrics = fetch_employee_day_metrics(cur, employee_id, target_date)

    return calculate_ghost_minutes(logged_minutes=metrics.logged_minutes)


def compute_index_of_trust_base(employee_id: int, target_date: date) -> float:
    """Compute base trust index for one employee/day from tasks_normalized."""

    with connection() as conn, conn.cursor() as cur:
        metrics = fetch_employee_day_metrics(cur, employee_id, target_date)

    return calculate_index_of_trust_base(
        total_tasks=metrics.total_tasks,
        none_count=metrics.none_count,
        unconfirmed_count=metrics.unconfirmed_count,
    )
