"""Task read endpoints."""

from __future__ import annotations

import asyncio
from datetime import date

from fastapi import APIRouter, Depends, Query

from WorkAI.api.dependencies import get_db, verify_api_key
from WorkAI.api.queries import fetch_aggregated_cycles, fetch_normalized_tasks, fetch_raw_tasks
from WorkAI.api.schemas import NormalizedTaskDTO, OperationalCycleDTO, RawTaskDTO
from WorkAI.db import connection

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(verify_api_key), Depends(get_db)])


def _load_raw(employee_id: int, task_date: date) -> list[RawTaskDTO]:
    with connection() as conn, conn.cursor() as cur:
        rows = fetch_raw_tasks(cur, employee_id, task_date)
    return [
        RawTaskDTO(
            raw_task_id=int(row[0]),
            spreadsheet_id=str(row[1]),
            sheet_title=str(row[2]),
            row_idx=int(row[3]),
            col_idx=int(row[4]),
            cell_a1=str(row[5]),
            cell_ingested_at=row[6],
            employee_name_raw=None if row[7] is None else str(row[7]),
            work_date=row[8],
            line_no=int(row[9]),
            line_text=str(row[10]),
            parsed_at=row[11],
        )
        for row in rows
    ]


def _load_normalized(employee_id: int, task_date: date) -> list[NormalizedTaskDTO]:
    with connection() as conn, conn.cursor() as cur:
        rows = fetch_normalized_tasks(cur, employee_id, task_date)
    return [
        NormalizedTaskDTO(
            id=int(row[0]),
            raw_task_id=None if row[1] is None else int(row[1]),
            employee_id=int(row[2]),
            task_date=row[3],
            canonical_text=str(row[4]),
            duration_minutes=None if row[5] is None else int(row[5]),
            task_category=None if row[6] is None else str(row[6]),
            time_source=str(row[7]),
            is_smart=bool(row[8]),
            is_micro=bool(row[9]),
            result_confirmed=bool(row[10]),
            is_zhdun=bool(row[11]),
            normalized_at=row[12],
            spreadsheet_id=str(row[13]),
            sheet_title=str(row[14]),
            row_idx=int(row[15]),
            col_idx=int(row[16]),
            line_no=int(row[17]),
        )
        for row in rows
    ]


def _load_aggregated(employee_id: int, task_date: date) -> list[OperationalCycleDTO]:
    with connection() as conn, conn.cursor() as cur:
        rows = fetch_aggregated_cycles(cur, employee_id, task_date)
    return [
        OperationalCycleDTO(
            id=int(row[0]),
            employee_id=int(row[1]),
            task_date=row[2],
            cycle_key=str(row[3]),
            canonical_text=str(row[4]),
            task_category=str(row[5]),
            total_duration_minutes=int(row[6]),
            tasks_count=int(row[7]),
            is_zhdun=bool(row[8]),
            avg_quality_score=None if row[9] is None else float(row[9]),
            avg_smart_score=None if row[10] is None else float(row[10]),
            created_at=row[11],
        )
        for row in rows
    ]


@router.get("/raw", response_model=list[RawTaskDTO])
async def get_raw_tasks(
    employee_id: int = Query(..., gt=0),
    task_date: date = Query(...),
) -> list[RawTaskDTO]:
    """Return raw task rows for one employee/day."""

    return await asyncio.to_thread(_load_raw, employee_id, task_date)


@router.get("/normalized", response_model=list[NormalizedTaskDTO])
async def get_normalized_tasks(
    employee_id: int = Query(..., gt=0),
    task_date: date = Query(...),
) -> list[NormalizedTaskDTO]:
    """Return normalized task rows for one employee/day."""

    return await asyncio.to_thread(_load_normalized, employee_id, task_date)


@router.get("/aggregated", response_model=list[OperationalCycleDTO])
async def get_aggregated_tasks(
    employee_id: int = Query(..., gt=0),
    task_date: date = Query(...),
) -> list[OperationalCycleDTO]:
    """Return operational cycles for one employee/day."""

    return await asyncio.to_thread(_load_aggregated, employee_id, task_date)
