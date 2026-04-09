"""Team overview endpoints."""

from __future__ import annotations

import asyncio
from datetime import date

from fastapi import APIRouter, Depends, Query

from WorkAI.api.dependencies import get_db, verify_api_key
from WorkAI.api.queries import fetch_team_overview
from WorkAI.api.schemas import TeamOverviewRowDTO
from WorkAI.db import connection

router = APIRouter(prefix="/team", tags=["team"], dependencies=[Depends(verify_api_key), Depends(get_db)])


def _load_team_overview(task_date: date) -> list[TeamOverviewRowDTO]:
    with connection() as conn, conn.cursor() as cur:
        rows = fetch_team_overview(cur, task_date)
    return [
        TeamOverviewRowDTO(
            employee_id=int(row[0]),
            task_date=row[1],
            ghost_minutes=int(row[2]),
            ghost_hours=float(row[3]),
            index_of_trust_base=float(row[4]),
            tasks_count=int(row[5]),
            cycles_count=int(row[6]),
        )
        for row in rows
    ]


@router.get("/overview", response_model=list[TeamOverviewRowDTO])
async def get_team_overview(task_date: date = Query(...)) -> list[TeamOverviewRowDTO]:
    """Return assess summary rows for one date across team."""

    return await asyncio.to_thread(_load_team_overview, task_date)
