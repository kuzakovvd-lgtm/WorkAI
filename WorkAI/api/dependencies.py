"""FastAPI dependencies (settings, auth, DB readiness)."""

from __future__ import annotations

import asyncio
import os

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from WorkAI.api.errors import http_error, unauthorized_error
from WorkAI.config import Settings, get_settings
from WorkAI.db import get_pool

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_app_settings() -> Settings:
    """Return cached application settings."""

    return get_settings()


async def get_db() -> None:
    """Ensure DB pool is available for request lifecycle."""

    await asyncio.to_thread(get_pool)


async def verify_api_key(
    settings: Settings = Depends(get_app_settings),
    provided_key: str | None = Security(_API_KEY_HEADER),
) -> None:
    """Validate X-API-Key for protected endpoints."""

    configured = (settings.api.api_key or "").strip()
    if configured == "":
        configured = os.getenv("WORKAI_API_KEY", "").strip()
    if configured == "":
        raise http_error(500, "config_error", "WORKAI_API_KEY is not configured")

    if provided_key is None or provided_key.strip() != configured:
        raise unauthorized_error()
