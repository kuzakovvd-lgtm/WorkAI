"""Assess layer models for ghost-time, scoring, and aggregation steps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class EmployeeDayKey:
    """One employee/day partition to process."""

    employee_id: int
    task_date: date


@dataclass(frozen=True)
class EmployeeDayMetrics:
    """Raw aggregates from tasks_normalized for one employee/day."""

    logged_minutes: int
    total_tasks: int
    none_count: int
    unconfirmed_count: int


@dataclass(frozen=True)
class EmployeeDailyGhostTimeRow:
    """Row payload for employee_daily_ghost_time upsert."""

    employee_id: int
    task_date: date
    workday_minutes: int
    logged_minutes: int
    ghost_minutes: int
    index_of_trust_base: Decimal


@dataclass(frozen=True)
class AssessGhostTimeResult:
    """Runner summary for one assess ghost-time execution."""

    target_date: date
    employees_processed: int
    rows_upserted: int


@dataclass(frozen=True)
class NormalizedTaskForScoring:
    """Minimal contract payload for task-level scoring."""

    normalized_task_id: int
    employee_id: int
    task_date: date
    duration_minutes: int | None
    time_source: str
    is_smart: bool
    is_micro: bool
    result_confirmed: bool
    is_zhdun: bool


@dataclass(frozen=True)
class DailyTaskAssessmentRow:
    """Row payload for daily_task_assessments upsert."""

    normalized_task_id: int
    employee_id: int
    task_date: date
    norm_minutes: int | None
    delta_minutes: int | None
    quality_score: Decimal | None
    smart_score: Decimal | None


@dataclass(frozen=True)
class AssessScoringResult:
    """Runner summary for task-scoring execution."""

    target_date: date
    tasks_scored: int
    rows_upserted: int
    employees_seen: int


@dataclass(frozen=True)
class AssessmentTaskForAggregation:
    """Joined normalized+scoring payload used by aggregation step."""

    normalized_task_id: int
    employee_id: int
    task_date: date
    spreadsheet_id: str
    sheet_title: str
    row_idx: int
    col_idx: int
    line_no: int
    canonical_text: str
    task_category: str | None
    duration_minutes: int | None
    is_micro: bool
    is_zhdun: bool
    quality_score: Decimal | None
    smart_score: Decimal | None


@dataclass(frozen=True)
class OperationalCycleRow:
    """Row payload for operational_cycles upsert."""

    employee_id: int
    task_date: date
    cycle_key: str
    canonical_text: str
    task_category: str
    total_duration_minutes: int
    tasks_count: int
    is_zhdun: bool
    avg_quality_score: Decimal | None
    avg_smart_score: Decimal | None


@dataclass(frozen=True)
class AssessAggregationResult:
    """Runner summary for aggregation execution."""

    target_date: date
    employees_processed: int
    cycles_written: int
    tasks_aggregated: int


@dataclass(frozen=True)
class AssessRunResult:
    """Combined assess run result (step1 + step2 + step3)."""

    target_date: date
    ghost_time: AssessGhostTimeResult
    scoring: AssessScoringResult
    aggregation: AssessAggregationResult
