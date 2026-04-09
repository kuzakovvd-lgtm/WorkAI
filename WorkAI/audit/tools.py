"""CrewAI tools used by audit agents."""

from __future__ import annotations

import importlib
import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from WorkAI.knowledge_base import lookup_methodology


class MethodologyLookupInput(BaseModel):
    """Tool input contract for methodology lookup."""

    query: str = Field(..., description="Methodology query string")
    limit: int = Field(default=5, ge=1, le=20)


if TYPE_CHECKING:

    class CrewBaseTool:
        """Typing-only fallback base class for tool contract."""

        name: str
        description: str
        args_schema: type[BaseModel]

else:  # pragma: no branch
    try:
        CrewBaseTool = importlib.import_module("crewai.tools").BaseTool
    except Exception:  # pragma: no cover - runtime fallback when crewai is unavailable

        class CrewBaseTool:
            """Fallback base class for local tests without CrewAI import."""

            name: str = "tool"
            description: str = ""
            args_schema: type[BaseModel] = MethodologyLookupInput


class MethodologyLookupTool(CrewBaseTool):
    """Lookup methodology recommendations from Phase 6 knowledge base."""

    name: str = "methodology_lookup"
    description: str = "Searches indexed methodology articles and returns top relevant excerpts."
    args_schema: type[BaseModel] = MethodologyLookupInput

    def _run(self, query: str, limit: int = 5) -> str:
        bounded_limit = max(1, min(limit, 20))
        results = lookup_methodology(query=query, limit=bounded_limit)
        payload: list[dict[str, Any]] = [
            {
                "source_path": item.source_path,
                "title": item.title,
                "body_excerpt": item.body_excerpt,
                "tags": item.tags,
                "rank": item.rank,
            }
            for item in results
        ]
        return json.dumps(payload, ensure_ascii=False)


def should_use_methodology_lookup(ghost_time_hours: float) -> bool:
    """Use methodology tool only for high-ghost-time cases in MVP."""

    return ghost_time_hours >= 4.0
