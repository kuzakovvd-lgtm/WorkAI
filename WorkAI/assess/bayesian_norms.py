"""Bayesian dynamic norms update for assess step 4."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from WorkAI.assess.models import DynamicTaskNormRow, TaskCategoryWindowStats

DEFAULT_BASELINE_PRIOR = Decimal("30")
DEFAULT_PRIOR_WEIGHT = Decimal("10")

# TODO(TZ §5.4): replace MVP priors with product methodology catalog.
BASELINE_PRIORS_MINUTES: dict[str, Decimal] = {
    "meetings": Decimal("30"),
    "coding": Decimal("60"),
    "review": Decimal("30"),
    "planning": Decimal("30"),
    "communication": Decimal("15"),
    "learning": Decimal("45"),
    "admin": Decimal("15"),
    "break": Decimal("15"),
    "uncategorized": Decimal("30"),
}


@dataclass(frozen=True)
class BayesianNormComputation:
    """Computed dynamic norm payload before DB write."""

    task_category: str
    norm_minutes: Decimal
    stddev_minutes: Decimal | None
    sample_size: int
    baseline_prior: Decimal


def compute_bayesian_norm(
    *,
    baseline_prior: Decimal,
    sample_mean: Decimal | None,
    sample_size: int,
    prior_weight: Decimal = DEFAULT_PRIOR_WEIGHT,
) -> Decimal:
    """Compute Bayesian-updated norm for one category."""

    baseline = max(Decimal("0"), baseline_prior)
    n = max(0, sample_size)
    if n == 0 or sample_mean is None:
        return baseline

    mean = max(Decimal("0"), sample_mean)
    numerator = (prior_weight * baseline) + (Decimal(n) * mean)
    denominator = prior_weight + Decimal(n)
    if denominator <= 0:
        return baseline

    return max(Decimal("0"), numerator / denominator)


def compute_norm_rows(
    *,
    stats: list[TaskCategoryWindowStats],
    baseline_priors: dict[str, Decimal] | None = None,
    prior_weight: Decimal = DEFAULT_PRIOR_WEIGHT,
) -> list[DynamicTaskNormRow]:
    """Build deterministic norm rows from observed window stats and baseline priors."""

    priors = baseline_priors or BASELINE_PRIORS_MINUTES
    by_category = {item.task_category: item for item in stats}
    categories = sorted(set(priors.keys()) | set(by_category.keys()))

    rows: list[DynamicTaskNormRow] = []
    for category in categories:
        observed = by_category.get(category)
        baseline = priors.get(category, DEFAULT_BASELINE_PRIOR)

        sample_size = 0 if observed is None else max(0, observed.sample_size)
        sample_mean = None if observed is None else observed.sample_mean
        stddev = None if observed is None else observed.sample_stddev_minutes

        norm = compute_bayesian_norm(
            baseline_prior=baseline,
            sample_mean=sample_mean,
            sample_size=sample_size,
            prior_weight=prior_weight,
        )

        rows.append(
            DynamicTaskNormRow(
                task_category=category,
                norm_minutes=_quantize_2(norm),
                stddev_minutes=None if stddev is None else _quantize_2(max(Decimal("0"), stddev)),
                sample_size=sample_size,
                baseline_prior=_quantize_2(max(Decimal("0"), baseline)),
            )
        )

    return rows


def resolve_window_bounds(anchor_date: date, window_days: int) -> tuple[date, date]:
    """Resolve inclusive date window bounds for Bayesian updates."""

    safe_days = max(1, window_days)
    return anchor_date - timedelta(days=safe_days - 1), anchor_date


def _quantize_2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
