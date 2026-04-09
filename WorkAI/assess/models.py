"""Assess layer models for ghost-time and task-scoring steps."""

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
class AssessRunResult:
    """Combined assess run result (step1 + step2)."""

    target_date: date
    ghost_time: AssessGhostTimeResult
    scoring: AssessScoringResult
