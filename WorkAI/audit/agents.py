"""CrewAI agent factories for audit phase."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

from WorkAI.common import ConfigError
from WorkAI.config import Settings


def _get_crewai_agent_class() -> Any:
    try:
        from crewai import Agent  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on optional runtime dependency
        raise ConfigError(
            "CrewAI is not installed. Install project dependencies with `pip install -e '.[dev]'`."
        ) from exc
    return Agent


def _ensure_openai_env(settings: Settings) -> None:
    if settings.audit.openai_api_key and os.getenv("OPENAI_API_KEY") is None:
        os.environ["OPENAI_API_KEY"] = settings.audit.openai_api_key


def build_operational_analyst(settings: Settings) -> Any:
    """Operational Efficiency Analyst (gpt-4o-mini by default)."""

    agent_cls = _get_crewai_agent_class()
    _ensure_openai_env(settings)
    return agent_cls(
        role="Operational Efficiency Analyst",
        goal=(
            "Detect CARE inefficiencies, quantify ghost-time contributors, "
            "and highlight anomalous operational cycles."
        ),
        backstory=(
            "You are an operations analyst focused on productivity signals, "
            "waste patterns, and execution bottlenecks from normalized cycle data."
        ),
        llm=settings.audit.model_analyst,
        max_iter=settings.audit.max_iter,
        max_rpm=settings.audit.max_rpm,
        max_retry_limit=settings.audit.openai_max_retries,
        allow_delegation=False,
        verbose=False,
    )


def build_data_integrity_forensic(settings: Settings) -> Any:
    """Data Integrity Forensic agent (gpt-4o-mini by default)."""

    agent_cls = _get_crewai_agent_class()
    _ensure_openai_env(settings)
    return agent_cls(
        role="Data Integrity Forensic",
        goal="Validate evidence quality and detect manipulation-like reporting patterns.",
        backstory=(
            "You are a forensic analyst focused on internal consistency, time-source reliability, "
            "and suspicious logging behavior."
        ),
        llm=settings.audit.model_forensic,
        max_iter=settings.audit.max_iter,
        max_rpm=settings.audit.max_rpm,
        max_retry_limit=settings.audit.openai_max_retries,
        allow_delegation=False,
        verbose=False,
    )


def build_strategic_reporter(settings: Settings, tools: Sequence[Any] | None = None) -> Any:
    """Strategic Management Reporter (gpt-4o by default)."""

    agent_cls = _get_crewai_agent_class()
    _ensure_openai_env(settings)
    return agent_cls(
        role="Strategic Management Reporter",
        goal="Synthesize executive summary and top management priorities from analyst outputs.",
        backstory=(
            "You transform analytical and forensic findings into concise executive actions "
            "that management can execute immediately."
        ),
        llm=settings.audit.model_reporter,
        max_iter=settings.audit.max_iter,
        max_rpm=settings.audit.max_rpm,
        max_retry_limit=settings.audit.openai_max_retries,
        allow_delegation=False,
        verbose=False,
        tools=list(tools or []),
    )
