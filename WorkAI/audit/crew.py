"""Audit orchestration: Crew build, run, cache semantics, usage telemetry."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import date
from typing import Any, cast
from uuid import UUID

from WorkAI.audit.agents import (
    build_data_integrity_forensic,
    build_operational_analyst,
    build_strategic_reporter,
)
from WorkAI.audit.models import AuditRunResult
from WorkAI.audit.queries import (
    fetch_prefetch_payload,
    find_completed_run,
    insert_run,
    mark_run_completed,
    mark_run_failed,
)
from WorkAI.audit.schemas import FinalAuditReport
from WorkAI.audit.tasks import build_forensic_task, build_operational_task, build_reporter_task
from WorkAI.audit.tools import MethodologyLookupTool, should_use_methodology_lookup
from WorkAI.common import ConfigError, DatabaseError, configure_logging, get_logger
from WorkAI.config import Settings, get_settings
from WorkAI.db import close_db, connection, init_db

_LOG = get_logger(__name__)


def _get_crewai_crew_types() -> tuple[type[Any], Any]:
    try:
        from crewai import Crew, Process
    except ImportError as exc:  # pragma: no cover - runtime dependency resolution
        raise ConfigError("CrewAI is not installed; audit run is unavailable") from exc
    return Crew, Process


def build_audit_crew(*, settings: Settings, use_methodology_tool: bool) -> Any:
    """Build sequential 3-agent crew for one audit run."""

    crew_cls, process_enum = _get_crewai_crew_types()

    analyst = build_operational_analyst(settings)
    forensic = build_data_integrity_forensic(settings)
    reporter_tools: list[Any] = [MethodologyLookupTool()] if use_methodology_tool else []
    reporter = build_strategic_reporter(settings, tools=reporter_tools)

    operational_task = build_operational_task(analyst)
    forensic_task = build_forensic_task(forensic, operational_task)
    reporter_task = build_reporter_task(reporter, operational_task, forensic_task)

    return crew_cls(
        agents=[analyst, forensic, reporter],
        tasks=[operational_task, forensic_task, reporter_task],
        process=process_enum.sequential,
        verbose=False,
    )


def run_audit(
    employee_id: int,
    task_date: date,
    *,
    force: bool = False,
    manage_db_lifecycle: bool = True,
    settings: Settings | None = None,
    crew_builder: Callable[..., Any] = build_audit_crew,
) -> AuditRunResult:
    """Run sequential audit with cache/force semantics and DB persistence."""

    resolved = settings or get_settings()
    configure_logging(resolved)

    if not resolved.audit.enabled:
        raise ConfigError("Audit is disabled. Set WORKAI_AUDIT__ENABLED=true")

    init_db(resolved)
    processing_run_id: UUID | None = None
    retry_attempts = int(getattr(resolved.audit, "failed_retry_attempts", 1))
    max_attempts = max(1, retry_attempts + 1)

    try:
        with connection() as conn, conn.cursor() as cur:
            if not force:
                completed = find_completed_run(cur, employee_id, task_date)
                if completed is not None and completed.report_json is not None:
                    cached_run = insert_run(
                        cur,
                        employee_id=employee_id,
                        task_date=task_date,
                        status="completed_cached",
                        report_json=completed.report_json,
                        error=None,
                        forced=False,
                    )
                    conn.commit()
                    _LOG.info(
                        "audit_returned_cached",
                        employee_id=employee_id,
                        task_date=task_date.isoformat(),
                        run_id=str(cached_run.id),
                    )
                    return AuditRunResult(
                        run_id=cached_run.id,
                        employee_id=employee_id,
                        task_date=task_date,
                        status="completed_cached",
                        report_json=cast(dict[str, object], cached_run.report_json),
                        cached=True,
                    )

            processing_run = insert_run(
                cur,
                employee_id=employee_id,
                task_date=task_date,
                status="processing",
                report_json=None,
                error=None,
                forced=force,
            )
            processing_run_id = processing_run.id
            conn.commit()

        for attempt in range(1, max_attempts + 1):
            started = time.perf_counter()
            try:
                with connection() as conn, conn.cursor() as cur:
                    payload = fetch_prefetch_payload(cur, employee_id, task_date)

                inputs = {
                    "employee_id": employee_id,
                    "task_date": task_date.isoformat(),
                    "index_of_trust_base": payload.index_of_trust_base,
                    "none_time_source_ratio": payload.none_time_source_ratio,
                    "non_smart_ratio": payload.non_smart_ratio,
                    "ghost_time_hours": payload.ghost_time_hours,
                    "aggregated_tasks_json": json.dumps(payload.aggregated_tasks, ensure_ascii=False),
                }

                crew = crew_builder(
                    settings=resolved,
                    use_methodology_tool=should_use_methodology_lookup(payload.ghost_time_hours),
                )
                crew_result = crew.kickoff(inputs=inputs)

                raw_report = _extract_report_payload(crew_result)
                merged_report = {
                    **raw_report,
                    "employee_id": employee_id,
                    "task_date": task_date,
                    "index_of_trust_base": payload.index_of_trust_base,
                    "none_time_source_ratio": payload.none_time_source_ratio,
                    "non_smart_ratio": payload.non_smart_ratio,
                    "ghost_time_hours": payload.ghost_time_hours,
                }
                report = FinalAuditReport.model_validate(merged_report)

                usage = _extract_usage(
                    crew_result=crew_result,
                    crew=crew,
                    duration_seconds=time.perf_counter() - started,
                )

                report_json = cast(dict[str, object], report.model_dump(mode="json"))
                report_json["_usage"] = usage

                with connection() as conn, conn.cursor() as cur:
                    mark_run_completed(cur, processing_run.id, report_json)
                    conn.commit()

                _LOG.info(
                    "audit_completed",
                    employee_id=employee_id,
                    task_date=task_date.isoformat(),
                    run_id=str(processing_run.id),
                    attempt=attempt,
                    attempts_total=max_attempts,
                )
                return AuditRunResult(
                    run_id=processing_run.id,
                    employee_id=employee_id,
                    task_date=task_date,
                    status="completed",
                    report_json=report_json,
                    cached=False,
                )
            except Exception as attempt_exc:
                error_text = str(attempt_exc)[:4000]
                _LOG.error(
                    "audit_attempt_failed_reason",
                    employee_id=employee_id,
                    task_date=task_date.isoformat(),
                    attempt=attempt,
                    attempts_total=max_attempts,
                    error_type=type(attempt_exc).__name__,
                    error=error_text,
                )
                if attempt < max_attempts:
                    _LOG.warning(
                        "audit_retry_scheduled",
                        employee_id=employee_id,
                        task_date=task_date.isoformat(),
                        next_attempt=attempt + 1,
                        attempts_total=max_attempts,
                    )
                    continue
                raise

    except Exception as exc:
        if processing_run_id is not None:
            error_text = str(exc)[:4000]
            _persist_failed_run(processing_run_id, error_text, resolved=resolved)
            _LOG.error(
                "audit_failed_reason",
                employee_id=employee_id,
                task_date=task_date.isoformat(),
                run_id=str(processing_run_id),
                attempts_total=max_attempts,
                error_type=type(exc).__name__,
                error=error_text,
            )
        _LOG.exception(
            "audit_failed",
            employee_id=employee_id,
            task_date=task_date.isoformat(),
            error_type=type(exc).__name__,
        )
        raise
    finally:
        if manage_db_lifecycle:
            close_db()


def _persist_failed_run(run_id: UUID, error: str, *, resolved: Settings) -> None:
    """Persist failed run status even if pool was closed during crew/tool execution."""

    try:
        with connection() as conn, conn.cursor() as cur:
            mark_run_failed(cur, run_id, error)
            conn.commit()
            return
    except DatabaseError:
        init_db(resolved)
        with connection() as conn, conn.cursor() as cur:
            mark_run_failed(cur, run_id, error)
            conn.commit()


def _extract_report_payload(crew_result: Any) -> dict[str, Any]:
    """Extract report dict from multiple CrewAI result formats."""

    if hasattr(crew_result, "pydantic") and crew_result.pydantic is not None:
        pydantic_obj = crew_result.pydantic
        if hasattr(pydantic_obj, "model_dump"):
            return cast(dict[str, Any], pydantic_obj.model_dump(mode="json"))

    if hasattr(crew_result, "json_dict") and isinstance(crew_result.json_dict, dict):
        return cast(dict[str, Any], crew_result.json_dict)

    if isinstance(crew_result, dict):
        return cast(dict[str, Any], crew_result)

    if hasattr(crew_result, "raw") and isinstance(crew_result.raw, str):
        try:
            parsed = json.loads(crew_result.raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Crew result raw output is not valid JSON") from exc
        if isinstance(parsed, dict):
            return parsed

    if isinstance(crew_result, str):
        parsed = json.loads(crew_result)
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Unsupported crew result format for final audit report")


def _extract_usage(*, crew_result: Any, crew: Any, duration_seconds: float) -> dict[str, Any]:
    """Best-effort extraction of usage/cost telemetry from crew result."""

    usage: dict[str, Any] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "by_agent": {},
        "cost_usd": 0.0,
        "duration_seconds": round(max(0.0, duration_seconds), 3),
    }

    try:
        candidates = [
            getattr(crew, "usage_metrics", None),
            getattr(crew_result, "usage_metrics", None),
            getattr(crew_result, "token_usage", None),
            getattr(crew_result, "_usage", None),
        ]

        for candidate in candidates:
            if isinstance(candidate, dict):
                input_tokens = candidate.get("input_tokens") or candidate.get("prompt_tokens") or 0
                output_tokens = candidate.get("output_tokens") or candidate.get("completion_tokens") or 0
                usage["input_tokens"] = max(int(usage["input_tokens"]), int(input_tokens))
                usage["output_tokens"] = max(int(usage["output_tokens"]), int(output_tokens))
                if isinstance(candidate.get("by_agent"), dict):
                    usage["by_agent"] = candidate["by_agent"]
                if candidate.get("cost_usd") is not None:
                    usage["cost_usd"] = float(candidate["cost_usd"])

        if usage["cost_usd"] == 0.0:
            inferred_cost = (usage["input_tokens"] * 0.15 + usage["output_tokens"] * 0.60) / 1_000_000
            usage["cost_usd"] = round(inferred_cost, 6)

    except Exception as exc:  # pragma: no cover - defensive telemetry path
        usage["_warning"] = f"usage extraction failed: {type(exc).__name__}"

    return usage
