"""Audit runner dataclasses and lightweight DB payload models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True)
class AuditPrefetchPayload:
    """Single prefetch snapshot passed into crew inputs."""

    employee_id: int
    task_date: date
    index_of_trust_base: float
    none_time_source_ratio: float
    non_smart_ratio: float
    ghost_time_hours: float
    aggregated_tasks: list[dict[str, object]]


@dataclass(frozen=True)
class AuditRunRecord:
    """Stored audit run metadata."""

    id: UUID
    employee_id: int
    task_date: date
    status: str
    started_at: datetime
    finished_at: datetime | None
    report_json: dict[str, object] | None
    forced: bool


@dataclass(frozen=True)
class AuditRunResult:
    """Runner return value used by CLI/tests."""

    run_id: UUID
    employee_id: int
    task_date: date
    status: str
    report_json: dict[str, object]
    cached: bool
