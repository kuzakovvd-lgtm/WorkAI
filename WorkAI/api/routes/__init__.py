"""API routers registry."""

from WorkAI.api.routes.analysis import router as analysis_router
from WorkAI.api.routes.debug import router as debug_router
from WorkAI.api.routes.health import router as health_router
from WorkAI.api.routes.tasks import router as tasks_router
from WorkAI.api.routes.team import router as team_router

__all__ = [
    "analysis_router",
    "debug_router",
    "health_router",
    "tasks_router",
    "team_router",
]
