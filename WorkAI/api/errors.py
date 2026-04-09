"""API error helpers and exception mapping."""

from __future__ import annotations

from fastapi import HTTPException, status


def make_error(code: str, message: str) -> dict[str, dict[str, str]]:
    """Build standardized error payload."""

    return {"error": {"code": code, "message": message}}


def http_error(status_code: int, code: str, message: str) -> HTTPException:
    """Create HTTPException with unified error detail."""

    return HTTPException(status_code=status_code, detail=make_error(code, message))


def unauthorized_error() -> HTTPException:
    """Create 401 unauthorized error payload."""

    return http_error(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Invalid API key")


def not_found_error(entity: str) -> HTTPException:
    """Create 404 error payload."""

    return http_error(status.HTTP_404_NOT_FOUND, "not_found", f"{entity} not found")
