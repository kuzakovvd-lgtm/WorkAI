"""Typed domain exceptions used across modules."""


class WorkAIError(Exception):
    """Base exception for WorkAI."""


class ConfigError(WorkAIError):
    """Configuration validation error."""


class DatabaseError(WorkAIError):
    """Database or connection pool error."""
