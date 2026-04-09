"""Audit analysis endpoints."""

from __future__ import annotations

import asyncio
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from WorkAI.api.dependencies import get_db, verify_api_key
from WorkAI.api.errors import not_found_error
from WorkAI.api.queries import fetch_audit_history, fetch_audit_run, insert_audit_feedback
from WorkAI.api.schemas import (
    AnalysisStartRequest,
    AnalysisStartResponse,
    AuditHistoryItemDTO,
    AuditRunStatusDTO,
    FeedbackRequest,
    FeedbackResponse,
)
from WorkAI.audit import run_audit
from WorkAI.db import connection

router = APIRouter(prefix="/analysis", tags=["analysis"], dependencies=[Depends(verify_api_key), Depends(get_db)])


def _start_analysis(payload: AnalysisStartRequest) -> AnalysisStartResponse:
    result = run_audit(payload.employee_id, payload.task_date, force=payload.force)
    return AnalysisStartResponse(
        run_id=result.run_id,
        employee_id=result.employee_id,
        task_date=result.task_date,
        status=result.status,
        cached=result.cached,
        report_json=result.report_json,
    )


def _load_status(run_id: UUID) -> AuditRunStatusDTO | None:
    with connection() as conn, conn.cursor() as cur:
        row = fetch_audit_run(cur, run_id)
    if row is None:
        return None
    return AuditRunStatusDTO(
        id=row[0],
        employee_id=int(row[1]),
        task_date=row[2],
        status=str(row[3]),
        started_at=row[4],
        finished_at=row[5],
        report_json=row[6],
        error=None if row[7] is None else str(row[7]),
        forced=bool(row[8]),
    )


def _load_history(employee_id: int, from_date: date | None, to_date: date | None) -> list[AuditHistoryItemDTO]:
    with connection() as conn, conn.cursor() as cur:
        rows = fetch_audit_history(cur, employee_id, from_date, to_date)
    return [
        AuditHistoryItemDTO(
            id=row[0],
            employee_id=int(row[1]),
            task_date=row[2],
            status=str(row[3]),
            started_at=row[4],
            finished_at=row[5],
            forced=bool(row[6]),
        )
        for row in rows
    ]


def _write_feedback(run_id: UUID, payload: FeedbackRequest, submitted_by_header: str | None) -> None:
    submitted_by = payload.submitted_by if payload.submitted_by is not None else submitted_by_header
    with connection() as conn, conn.cursor() as cur:
        insert_audit_feedback(cur, run_id, payload.rating, payload.comment, submitted_by)
        conn.commit()


@router.post("/start", response_model=AnalysisStartResponse)
async def start_analysis(payload: AnalysisStartRequest) -> AnalysisStartResponse:
    """Start audit run for one employee/day."""

    return await asyncio.to_thread(_start_analysis, payload)


@router.get("/status/{run_id}", response_model=AuditRunStatusDTO)
async def get_analysis_status(run_id: UUID) -> AuditRunStatusDTO:
    """Return current status/report for one audit run."""

    status_payload = await asyncio.to_thread(_load_status, run_id)
    if status_payload is None:
        raise not_found_error("audit run")
    return status_payload


@router.get("/history", response_model=list[AuditHistoryItemDTO])
async def get_analysis_history(
    employee_id: int = Query(..., gt=0),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> list[AuditHistoryItemDTO]:
    """Return audit run history for employee and optional date range."""

    return await asyncio.to_thread(_load_history, employee_id, from_date, to_date)


@router.post("/{run_id}/feedback", response_model=FeedbackResponse)
async def post_analysis_feedback(
    run_id: UUID,
    payload: FeedbackRequest,
    submitted_by: str | None = Header(default=None, alias="X-Submitted-By"),
) -> FeedbackResponse:
    """Attach feedback to one audit run."""

    await asyncio.to_thread(_write_feedback, run_id, payload, submitted_by)
    return FeedbackResponse(run_id=run_id, status="recorded")
