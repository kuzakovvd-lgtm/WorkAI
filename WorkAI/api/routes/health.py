"""Health endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from WorkAI.api.dependencies import get_app_settings, verify_api_key
from WorkAI.api.queries import fetch_health_deep
from WorkAI.api.schemas import DeepHealthResponse, HealthResponse
from WorkAI.config import Settings
from WorkAI.db import connection

router = APIRouter(tags=["health"])


def _run_deep_check(settings: Settings) -> DeepHealthResponse:
    with connection() as conn, conn.cursor() as cur:
        db_ok, alembic_version = fetch_health_deep(cur)
    return DeepHealthResponse(
        status="ok",
        service=settings.app.service_name,
        version=settings.app.version,
        db_ok=db_ok,
        alembic_version=alembic_version,
    )


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """Liveness probe without authentication."""

    return HealthResponse(status="ok", service=settings.app.service_name)


@router.get("/health/deep", response_model=DeepHealthResponse, dependencies=[Depends(verify_api_key)])
async def health_deep(settings: Settings = Depends(get_app_settings)) -> DeepHealthResponse:
    """Deep health probe with DB connectivity check."""

    return await asyncio.to_thread(_run_deep_check, settings)
