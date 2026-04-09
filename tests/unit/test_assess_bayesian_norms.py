from __future__ import annotations

from datetime import date
from decimal import Decimal

from WorkAI.assess.bayesian_norms import (
    BASELINE_PRIORS_MINUTES,
    compute_bayesian_norm,
    compute_norm_rows,
    resolve_window_bounds,
)
from WorkAI.assess.models import TaskCategoryWindowStats


def test_bayesian_formula_matches_spec() -> None:
    result = compute_bayesian_norm(
        baseline_prior=Decimal("60"),
        sample_mean=Decimal("30"),
        sample_size=5,
        prior_weight=Decimal("10"),
    )
    # (10*60 + 5*30) / (10+5) = 50
    assert result == Decimal("50")


def test_n_zero_falls_back_to_prior() -> None:
    assert compute_bayesian_norm(baseline_prior=Decimal("30"), sample_mean=None, sample_size=0) == Decimal("30")


def test_norm_is_never_negative() -> None:
    result = compute_bayesian_norm(
        baseline_prior=Decimal("-10"),
        sample_mean=Decimal("-5"),
        sample_size=4,
        prior_weight=Decimal("10"),
    )
    assert result == Decimal("0")


def test_compute_norm_rows_uses_baseline_for_missing_categories() -> None:
    stats = [
        TaskCategoryWindowStats(
            task_category="coding",
            sample_size=2,
            sample_mean=Decimal("90"),
            sample_stddev_minutes=Decimal("10"),
        )
    ]
    rows = compute_norm_rows(stats=stats)
    by_category = {row.task_category: row for row in rows}

    assert by_category["coding"].sample_size == 2
    assert by_category["coding"].norm_minutes == Decimal("65.00")

    assert by_category["uncategorized"].sample_size == 0
    assert by_category["uncategorized"].norm_minutes == BASELINE_PRIORS_MINUTES["uncategorized"]


def test_window_bounds_are_inclusive() -> None:
    start, end = resolve_window_bounds(date(2026, 4, 15), 7)
    assert start.isoformat() == "2026-04-09"
    assert end.isoformat() == "2026-04-15"
