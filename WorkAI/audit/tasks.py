"""CrewAI task definitions for sequential audit flow."""

from __future__ import annotations

from typing import Any

from WorkAI.audit.schemas import DataIntegrityOutput, FinalAuditReport, OperationalEfficiencyOutput
from WorkAI.common import ConfigError


def _get_crewai_task_class() -> Any:
    try:
        from crewai import Task  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on optional runtime dependency
        raise ConfigError("CrewAI is not installed; cannot build audit tasks") from exc
    return Task


def build_operational_task(agent: Any) -> Any:
    """First task: operational inefficiency analysis."""

    task_cls = _get_crewai_task_class()
    return task_cls(
        description=(
            "Analyze aggregated operational cycles for employee {employee_id} at date {task_date}. "
            "Use aggregated_tasks_json and produce concise inefficiency findings."
        ),
        expected_output="Structured operational inefficiency findings.",
        output_pydantic=OperationalEfficiencyOutput,
        agent=agent,
    )


def build_forensic_task(agent: Any, context_task: Any) -> Any:
    """Second task: forensic integrity review."""

    task_cls = _get_crewai_task_class()
    return task_cls(
        description=(
            "Review data integrity for employee {employee_id}/{task_date} using prefetched metrics and "
            "the operational analyst output."
        ),
        expected_output="Structured forensic integrity output with risk signals.",
        output_pydantic=DataIntegrityOutput,
        agent=agent,
        context=[context_task],
    )


def build_reporter_task(agent: Any, operational_task: Any, forensic_task: Any) -> Any:
    """Third task: final strategic report."""

    task_cls = _get_crewai_task_class()
    return task_cls(
        description=(
            "Produce final executive report for employee {employee_id}/{task_date}. "
            "You must synthesize prior task outputs and prefetched metrics into final JSON report."
        ),
        expected_output="Final audit report in structured JSON format.",
        output_pydantic=FinalAuditReport,
        agent=agent,
        context=[operational_task, forensic_task],
    )
