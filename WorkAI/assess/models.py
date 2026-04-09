"""Assess data models for ghost time step."""

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
