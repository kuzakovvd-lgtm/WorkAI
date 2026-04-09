"""Assess runner for Phase 5 Step 1/2/3/4: ghost time, scoring, aggregation, norms."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from WorkAI.assess.aggregation import aggregate_operational_cycles
from WorkAI.assess.bayesian_norms import compute_norm_rows, resolve_window_bounds
from WorkAI.assess.ghost_time import calculate_ghost_minutes, calculate_index_of_trust_base
from WorkAI.assess.models import (
    AssessAggregationResult,
    AssessBayesianNormsResult,
    AssessGhostTimeResult,
    AssessmentTaskForAggregation,
    AssessRunResult,
    AssessScoringResult,
    DailyTaskAssessmentRow,
    EmployeeDailyGhostTimeRow,
    OperationalCycleRow,
)
from WorkAI.assess.queries import (
    delete_operational_cycles_for_employee_day,
    fetch_aggregation_input_by_date,
    fetch_employee_day_metrics,
    fetch_scoring_tasks_by_date,
    fetch_window_category_stats,
    list_employee_day_keys,
    recompute_assessment_norms_for_date,
    recompute_assessment_norms_for_window,
    upsert_daily_task_assessments_batch,
    upsert_dynamic_task_norms_batch,
    upsert_employee_daily_ghost_time_batch,
    upsert_operational_cycles_batch,
)
from WorkAI.assess.scoring import compute_quality_score, compute_smart_score
from WorkAI.common import configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db

_LOG = get_logger(__name__)


def _quantize_score(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def _quantize_decimal(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


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
                            index_of_trust_base=_quantize_score(trust_base),
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


def run_assess_scoring(target_date: date, settings: Settings | None = None) -> AssessScoringResult:
    """Run task-level scoring step for a specific date."""

    resolved = settings or get_settings()
    configure_logging(resolved)
    init_db(resolved)

    rows_to_upsert: list[DailyTaskAssessmentRow] = []
    employees_seen: set[int] = set()

    try:
        with connection() as conn:
            with conn.cursor() as cur:
                tasks = fetch_scoring_tasks_by_date(cur, target_date)

                for task in tasks:
                    employees_seen.add(task.employee_id)
                    rows_to_upsert.append(
                        DailyTaskAssessmentRow(
                            normalized_task_id=task.normalized_task_id,
                            employee_id=task.employee_id,
                            task_date=task.task_date,
                            norm_minutes=None,
                            delta_minutes=None,
                            quality_score=_quantize_score(compute_quality_score(task)),
                            smart_score=_quantize_score(compute_smart_score(task)),
                        )
                    )

                upsert_daily_task_assessments_batch(cur, rows_to_upsert)
            conn.commit()
    finally:
        close_db()

    result = AssessScoringResult(
        target_date=target_date,
        tasks_scored=len(rows_to_upsert),
        rows_upserted=len(rows_to_upsert),
        employees_seen=len(employees_seen),
    )
    _LOG.info(
        "assess_scoring_completed",
        target_date=target_date.isoformat(),
        tasks_scored=result.tasks_scored,
        rows_upserted=result.rows_upserted,
        employees_seen=result.employees_seen,
    )
    return result


def run_assess_aggregation(target_date: date, settings: Settings | None = None) -> AssessAggregationResult:
    """Run deterministic aggregation into operational_cycles for target date."""

    resolved = settings or get_settings()
    configure_logging(resolved)
    init_db(resolved)
    grouped: dict[tuple[int, date], list[AssessmentTaskForAggregation]] = defaultdict(list)
    cycles_written = 0
    tasks_aggregated = 0

    try:
        with connection() as conn:
            with conn.cursor() as cur:
                input_rows = fetch_aggregation_input_by_date(cur, target_date)
                for row in input_rows:
                    grouped[(row.employee_id, row.task_date)].append(row)

                for (employee_id, day), rows in grouped.items():
                    cycles = aggregate_operational_cycles(rows)
                    quantized_cycles = [
                        OperationalCycleRow(
                            employee_id=cycle.employee_id,
                            task_date=cycle.task_date,
                            cycle_key=cycle.cycle_key,
                            canonical_text=cycle.canonical_text,
                            task_category=cycle.task_category,
                            total_duration_minutes=cycle.total_duration_minutes,
                            tasks_count=cycle.tasks_count,
                            is_zhdun=cycle.is_zhdun,
                            avg_quality_score=_quantize_decimal(cycle.avg_quality_score),
                            avg_smart_score=_quantize_decimal(cycle.avg_smart_score),
                        )
                        for cycle in cycles
                    ]

                    # MVP strategy: delete+rebuild per employee/date to avoid stale cycles
                    # when upstream normalize/scoring data changes between runs.
                    delete_operational_cycles_for_employee_day(cur, employee_id, day)
                    upsert_operational_cycles_batch(cur, quantized_cycles)
                    cycles_written += len(quantized_cycles)
                    tasks_aggregated += len(rows)

            conn.commit()
    finally:
        close_db()

    result = AssessAggregationResult(
        target_date=target_date,
        employees_processed=len(grouped),
        cycles_written=cycles_written,
        tasks_aggregated=tasks_aggregated,
    )
    _LOG.info(
        "assess_aggregation_completed",
        target_date=target_date.isoformat(),
        employees_processed=result.employees_processed,
        cycles_written=result.cycles_written,
        tasks_aggregated=result.tasks_aggregated,
    )
    return result


def run_assess_bayesian_norms(
    target_date: date | None = None,
    window_days: int = 7,
    settings: Settings | None = None,
) -> AssessBayesianNormsResult:
    """Update dynamic_task_norms and recompute assessment norm/delta fields."""

    resolved = settings or get_settings()
    configure_logging(resolved)
    init_db(resolved)

    anchor_date = target_date or date.today()
    window_start, window_end = resolve_window_bounds(anchor_date, window_days)

    categories_updated = 0
    rows_recomputed = 0

    try:
        with connection() as conn:
            with conn.cursor() as cur:
                stats = fetch_window_category_stats(cur, window_start, window_end)
                norm_rows = compute_norm_rows(stats=stats)
                upsert_dynamic_task_norms_batch(cur, norm_rows)
                categories_updated = len(norm_rows)

                if target_date is None:
                    rows_recomputed = recompute_assessment_norms_for_window(cur, window_start, window_end)
                else:
                    rows_recomputed = recompute_assessment_norms_for_date(cur, target_date)
            conn.commit()
    finally:
        close_db()

    result = AssessBayesianNormsResult(
        target_date=anchor_date,
        window_days=max(1, window_days),
        categories_updated=categories_updated,
        rows_recomputed=rows_recomputed,
    )
    _LOG.info(
        "assess_bayesian_norms_completed",
        target_date=result.target_date.isoformat(),
        window_days=result.window_days,
        categories_updated=result.categories_updated,
        rows_recomputed=result.rows_recomputed,
    )
    return result


def run_assess(target_date: date, settings: Settings | None = None) -> AssessRunResult:
    """Run assess step1+step2+step3+step4 for a specific date in sequence."""

    resolved = settings or get_settings()
    configure_logging(resolved)

    ghost = run_assess_ghost_time(target_date, settings=resolved)
    scoring = run_assess_scoring(target_date, settings=resolved)
    aggregation = run_assess_aggregation(target_date, settings=resolved)
    bayesian_norms = run_assess_bayesian_norms(target_date, window_days=7, settings=resolved)

    result = AssessRunResult(
        target_date=target_date,
        ghost_time=ghost,
        scoring=scoring,
        aggregation=aggregation,
        bayesian_norms=bayesian_norms,
    )
    _LOG.info(
        "assess_run_completed",
        target_date=target_date.isoformat(),
        ghost_rows_upserted=ghost.rows_upserted,
        scoring_rows_upserted=scoring.rows_upserted,
        aggregation_cycles_written=aggregation.cycles_written,
        bayesian_rows_recomputed=bayesian_norms.rows_recomputed,
    )
    return result
