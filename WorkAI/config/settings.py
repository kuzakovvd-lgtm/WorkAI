"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from WorkAI import __version__


class AppSettings(BaseModel):
    """General application metadata."""

    env: Literal["dev", "staging", "prod"] = "dev"
    service_name: str = "workai"
    version: str = __version__


class LoggingSettings(BaseModel):
    """Logging behavior settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    json_output: bool = Field(default=False, alias="json")


class DatabaseSettings(BaseModel):
    """PostgreSQL connection pool settings."""

    dsn: str | None = None
    min_size: int = 1
    max_size: int = 5
    timeout_sec: float = 10.0
    connect_timeout_sec: float = 5.0
    lock_timeout_ms: int = 2000
    exit_on_pool_failure: bool = False

    def require_dsn(self) -> str:
        """Return DSN or raise a clear configuration error."""

        if self.dsn is None or self.dsn.strip() == "":
            raise ValueError(
                "Database DSN is not configured. Set WORKAI_DB__DSN="
                "postgresql://user:pass@host:port/dbname"
            )
        return self.dsn.strip()


class Settings(BaseSettings):
    """Root settings object for the service."""

    model_config = SettingsConfigDict(
        env_prefix="WORKAI_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    env: Literal["dev", "staging", "prod"] = "dev"
    app: AppSettings = Field(default_factory=AppSettings)
    log: LoggingSettings = Field(default_factory=LoggingSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)

    @model_validator(mode="after")
    def sync_root_env_to_app(self) -> Settings:
        """Keep WORKAI_ENV as the canonical env selector for app metadata."""

        self.app.env = self.env
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide cached settings."""

    return Settings()
