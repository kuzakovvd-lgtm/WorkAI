"""Pure rule helpers for notification decisioning."""

from __future__ import annotations


def should_alert_on_cost_spike(today_cost: float, history: list[float]) -> bool:
    """Return true when today's cost is significantly above historical baseline.

    Rule (MVP):
    - require at least 3 historical points;
    - if average history is <= 0, alert only when today_cost > 0;
    - alert when today_cost >= average * 1.5.
    """

    if len(history) < 3:
        return False

    average = sum(history) / float(len(history))
    if average <= 0:
        return today_cost > 0

    return today_cost >= (average * 1.5)


def should_alert_on_failed_runs(failed_runs: int, total_runs: int) -> bool:
    """Return true when failed run ratio exceeds operational threshold.

    Rule (MVP):
    - no runs -> no alert;
    - require at least 3 failed runs;
    - and failed ratio >= 0.20.
    """

    if total_runs <= 0:
        return False
    if failed_runs < 3:
        return False

    return (failed_runs / float(total_runs)) >= 0.20
