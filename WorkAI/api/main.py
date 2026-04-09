"""FastAPI application factory and wiring."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response

from WorkAI import __version__
from WorkAI.api.errors import make_error
from WorkAI.api.routes import (
    analysis_router,
    debug_router,
    health_router,
    tasks_router,
    team_router,
)
from WorkAI.common import ConfigError, WorkAIError, configure_logging
from WorkAI.config import get_settings
from WorkAI.db import close_db, init_db

_API_HEADER_VERSION = __version__.split("-", maxsplit=1)[0]


@asynccontextmanager
async def lifespan(_: FastAPI) -> Any:
    """Initialize and close shared resources for API runtime."""

    settings = get_settings()
    configure_logging(settings)

    configured_api_key = (settings.api.api_key or "").strip()
    if configured_api_key == "":
        configured_api_key = os.getenv("WORKAI_API_KEY", "").strip()
    if configured_api_key == "":
        raise ConfigError("WORKAI_API_KEY is required to start API")

    init_db(settings)
    try:
        yield
    finally:
        close_db()


app = FastAPI(title="WorkAI API", version=_API_HEADER_VERSION, lifespan=lifespan)


@app.middleware("http")
async def add_version_header(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach API version header on every response."""

    response = await call_next(request)
    response.headers["X-WorkAI-Version"] = _API_HEADER_VERSION
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """Return unified JSON error shape for HTTPException."""

    if isinstance(exc.detail, dict) and "error" in exc.detail:
        payload = exc.detail
    else:
        payload = make_error("http_error", str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation failures in unified JSON format."""

    first = exc.errors()[0] if exc.errors() else {"msg": "Validation error"}
    return JSONResponse(
        status_code=422,
        content=make_error("validation_error", str(first.get("msg", "Validation error"))),
    )


@app.exception_handler(WorkAIError)
async def workai_exception_handler(_: Request, exc: WorkAIError) -> JSONResponse:
    """Return known domain errors without stack leakage."""

    return JSONResponse(status_code=500, content=make_error("workai_error", str(exc)))


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, __: Exception) -> JSONResponse:
    """Return generic internal error payload for unexpected exceptions."""

    return JSONResponse(status_code=500, content=make_error("internal_error", "Internal server error"))


app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(analysis_router)
app.include_router(team_router)
app.include_router(debug_router)
