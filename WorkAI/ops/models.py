"""Ops result models for healthcheck, sweeper, rollup, unit verification and cutover."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

Severity = Literal["info", "data_warning", "infra_critical"]


@dataclass(frozen=True)
class CheckResult:
    """One healthcheck item result."""

    name: str
    status: Literal["ok", "warning", "critical", "unknown", "not_applicable"]
    severity: Severity
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HealthcheckResult:
    """Aggregated healthcheck output."""

    severity: Severity
    checks: list[CheckResult]
    generated_at: datetime


@dataclass(frozen=True)
class StaleSweepResult:
    """Stale sweeper summary."""

    tables_checked: list[str]
    rows_updated: int
    per_table: dict[str, int]
    threshold_minutes: int
    finished_at: datetime


@dataclass(frozen=True)
class CostRollupResult:
    """Daily cost rollup summary."""

    rollup_date: date
    runs_seen: int
    usage_rows_used: int
    usage_rows_skipped: int
    runs_count: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cost_spike_detected: bool
    finished_at: datetime


@dataclass(frozen=True)
class UnitCheckResult:
    """One systemd unit path validation result."""

    unit_name: str
    execstart: str
    working_directory: str | None
    interpreter_path: str | None
    script_path: str | None
    interpreter_exists: bool
    script_exists: bool
    path_policy_ok: bool
    status: Literal["ok", "warning", "critical"]


@dataclass(frozen=True)
class VerifyUnitsResult:
    """Aggregate verify-units output."""

    unit_dir: str
    units_checked: int
    units: list[UnitCheckResult]
    severity: Severity
    generated_at: datetime


@dataclass(frozen=True)
class ParallelDiffItem:
    """One table-level difference item for v1/v2 parallel-run check."""

    table: str
    reference_count: int
    candidate_count: int
    delta: int
    delta_pct: float
    within_tolerance: bool


@dataclass(frozen=True)
class ParallelDiffResult:
    """Parallel-run comparison output for one target date."""

    target_date: date
    tolerance_pct: float
    reference_counts: dict[str, int]
    candidate_counts: dict[str, int]
    diffs: list[ParallelDiffItem]
    violations: list[str]
    generated_at: datetime


@dataclass(frozen=True)
class CutoverReadinessResult:
    """Cutover readiness checklist result."""

    status: Literal["ready", "risky", "blocked"]
    canonical_path: str
    current_path: str
    checks: list[CheckResult]
    blockers: list[str]
    residual_risks: list[str]
    generated_at: datetime
