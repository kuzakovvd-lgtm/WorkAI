"""Debug read endpoints."""

from __future__ import annotations

import asyncio
from datetime import date

from fastapi import APIRouter, Depends, Query

from WorkAI.api.dependencies import get_db, verify_api_key
from WorkAI.api.queries import (
    fetch_debug_cost,
    fetch_debug_logs,
    fetch_result_confirmed_daily_report,
)
from WorkAI.api.schemas import DebugCostRowDTO, DebugLogRowDTO, ResultConfirmedDailyRowDTO
from WorkAI.db import connection

router = APIRouter(prefix="/debug", tags=["debug"], dependencies=[Depends(verify_api_key), Depends(get_db)])


def _load_logs(limit: int) -> list[DebugLogRowDTO]:
    with connection() as conn, conn.cursor() as cur:
        rows = fetch_debug_logs(cur, limit)
    return [
        DebugLogRowDTO(
            source=str(row[0]),
            created_at=row[1],
            phase=str(row[2]),
            run_id=None if row[3] is None else str(row[3]),
            source_ref=str(row[4]),
            error_type=str(row[5]),
            error_message=str(row[6]),
        )
        for row in rows
    ]


def _load_cost(from_date: date | None, to_date: date | None) -> list[DebugCostRowDTO]:
    with connection() as conn, conn.cursor() as cur:
        rows = fetch_debug_cost(cur, from_date, to_date)
    return [
        DebugCostRowDTO(
            rollup_date=row[0],
            runs_count=int(row[1]),
            input_tokens=int(row[2]),
            output_tokens=int(row[3]),
            cost_usd=float(row[4]),
            rollup_at=row[5],
        )
        for row in rows
    ]


def _load_result_confirmed_daily(to_date: date | None) -> list[ResultConfirmedDailyRowDTO]:
    with connection() as conn, conn.cursor() as cur:
        rows = fetch_result_confirmed_daily_report(cur, to_date)
    return [
        ResultConfirmedDailyRowDTO(
            task_date=row[0],
            total=int(row[1]),
            done=int(row[2]),
            pct=float(row[3]),
        )
        for row in rows
    ]


@router.get("/logs", response_model=list[DebugLogRowDTO])
async def get_debug_logs(limit: int = Query(default=50, ge=1, le=500)) -> list[DebugLogRowDTO]:
    """Return latest pipeline and audit failure events."""

    return await asyncio.to_thread(_load_logs, limit)


@router.get("/cost", response_model=list[DebugCostRowDTO])
async def get_debug_cost(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> list[DebugCostRowDTO]:
    """Return daily audit cost rollup rows."""

    return await asyncio.to_thread(_load_cost, from_date, to_date)


@router.get("/result-confirmed-daily", response_model=list[ResultConfirmedDailyRowDTO])
async def get_result_confirmed_daily(
    to_date: date | None = Query(default=None, alias="to"),
) -> list[ResultConfirmedDailyRowDTO]:
    """Return daily result_confirmed KPI rows."""

    return await asyncio.to_thread(_load_result_confirmed_daily, to_date)
