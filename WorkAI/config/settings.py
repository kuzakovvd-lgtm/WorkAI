"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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


class GoogleSheetsSettings(BaseModel):
    """Google Sheets ingestion configuration."""

    enabled: bool = False
    spreadsheet_id: str | None = None
    ranges: Annotated[list[str], NoDecode] = Field(default_factory=list)
    service_account_file: str | None = None
    service_account_json_b64: str | None = None
    read_only: bool = True
    request_timeout_sec: float = 30.0
    max_retries: int = 5
    backoff_base_sec: float = 0.5
    batch_ranges: int = 20
    value_render_option: Literal["FORMATTED_VALUE", "UNFORMATTED_VALUE"] = "FORMATTED_VALUE"
    date_time_render_option: Literal["FORMATTED_STRING", "SERIAL_NUMBER"] = "FORMATTED_STRING"

    @field_validator("ranges", mode="before")
    @classmethod
    def parse_ranges_csv(cls, value: object) -> object:
        """Allow CSV string in WORKAI_GSHEETS__RANGES env var."""

        if isinstance(value, str):
            parsed = [part.strip() for part in value.split(",") if part.strip()]
            return parsed
        return value

    @model_validator(mode="after")
    def validate_when_enabled(self) -> GoogleSheetsSettings:
        """Validate required fields for enabled ingest mode."""

        if not self.enabled:
            return self

        if self.spreadsheet_id is None or self.spreadsheet_id.strip() == "":
            raise ValueError("WORKAI_GSHEETS__SPREADSHEET_ID is required when gsheets.enabled=true")

        if not self.ranges:
            raise ValueError("WORKAI_GSHEETS__RANGES must be non-empty when gsheets.enabled=true")

        has_file = self.service_account_file is not None and self.service_account_file.strip() != ""
        has_b64 = self.service_account_json_b64 is not None and self.service_account_json_b64.strip() != ""
        if not (has_file or has_b64):
            raise ValueError(
                "Set WORKAI_GSHEETS__SERVICE_ACCOUNT_FILE or "
                "WORKAI_GSHEETS__SERVICE_ACCOUNT_JSON_B64 when gsheets.enabled=true"
            )

        if self.batch_ranges <= 0:
            raise ValueError("WORKAI_GSHEETS__BATCH_RANGES must be positive")

        if self.max_retries < 0:
            raise ValueError("WORKAI_GSHEETS__MAX_RETRIES must be >= 0")

        return self


class ParseSettings(BaseModel):
    """Parse layer runtime settings."""

    enabled: bool = False
    header_row_idx: int = 1
    employee_col_idx: int = 1
    max_cells_per_sheet: int = 20000
    date_formats: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["%Y-%m-%d", "%d.%m.%Y"]
    )

    @field_validator("date_formats", mode="before")
    @classmethod
    def parse_date_formats_csv(cls, value: object) -> object:
        """Allow comma-separated date formats in environment values."""

        if isinstance(value, str):
            parsed = [part.strip() for part in value.split(",") if part.strip()]
            return parsed
        return value

    @model_validator(mode="after")
    def validate_when_enabled(self) -> ParseSettings:
        """Validate parse settings only for active parse runs."""

        if not self.enabled:
            return self

        if self.header_row_idx <= 0:
            raise ValueError("WORKAI_PARSE__HEADER_ROW_IDX must be > 0 when parse.enabled=true")
        if self.employee_col_idx <= 0:
            raise ValueError("WORKAI_PARSE__EMPLOYEE_COL_IDX must be > 0 when parse.enabled=true")
        if self.max_cells_per_sheet <= 0:
            raise ValueError("WORKAI_PARSE__MAX_CELLS_PER_SHEET must be > 0 when parse.enabled=true")
        if not self.date_formats:
            raise ValueError("WORKAI_PARSE__DATE_FORMATS must be non-empty when parse.enabled=true")

        return self


class NormalizeSettings(BaseModel):
    """Normalize layer runtime settings."""

    enabled: bool = False
    employee_aliases_file: str | None = None
    fuzzy_enabled: bool = False
    fuzzy_threshold: int = 90
    time_parse_enabled: bool = True
    category_rules_file: str | None = None
    max_rows_per_sheet: int = 200000
    max_errors_per_sheet: int = 50

    @model_validator(mode="after")
    def validate_when_enabled(self) -> NormalizeSettings:
        """Validate normalize settings only for active normalize runs."""

        if not self.enabled:
            return self

        if self.fuzzy_threshold < 0 or self.fuzzy_threshold > 100:
            raise ValueError("WORKAI_NORMALIZE__FUZZY_THRESHOLD must be in range [0, 100]")

        if self.max_rows_per_sheet <= 0:
            raise ValueError("WORKAI_NORMALIZE__MAX_ROWS_PER_SHEET must be > 0")
        if self.max_errors_per_sheet <= 0:
            raise ValueError("WORKAI_NORMALIZE__MAX_ERRORS_PER_SHEET must be > 0")

        if self.employee_aliases_file is not None and self.employee_aliases_file.strip() == "":
            raise ValueError("WORKAI_NORMALIZE__EMPLOYEE_ALIASES_FILE must not be empty when set")

        if self.category_rules_file is not None and self.category_rules_file.strip() == "":
            raise ValueError("WORKAI_NORMALIZE__CATEGORY_RULES_FILE must not be empty when set")

        return self


class AuditSettings(BaseModel):
    """Audit layer runtime and model configuration."""

    enabled: bool = False
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    model_analyst: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL_ANALYST")
    model_forensic: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL_FORENSIC")
    model_reporter: str = Field(default="gpt-4o", validation_alias="OPENAI_MODEL_REPORTER")
    openai_max_retries: int = Field(default=2, validation_alias="OPENAI_MAX_RETRIES")
    max_iter: int = 5
    max_rpm: int = 10

    @model_validator(mode="after")
    def validate_limits(self) -> AuditSettings:
        """Validate audit runtime limits."""

        if self.max_iter <= 0:
            raise ValueError("WORKAI_AUDIT__MAX_ITER must be > 0")
        if self.max_rpm <= 0:
            raise ValueError("WORKAI_AUDIT__MAX_RPM must be > 0")
        if self.openai_max_retries < 0:
            raise ValueError("OPENAI_MAX_RETRIES must be >= 0")
        return self


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
    gsheets: GoogleSheetsSettings = Field(default_factory=GoogleSheetsSettings)
    parse: ParseSettings = Field(default_factory=ParseSettings)
    normalize: NormalizeSettings = Field(default_factory=NormalizeSettings)
    audit: AuditSettings = Field(default_factory=AuditSettings)

    @model_validator(mode="after")
    def sync_root_env_to_app(self) -> Settings:
        """Keep WORKAI_ENV as the canonical env selector for app metadata."""

        self.app.env = self.env
        if self.audit.openai_api_key is None:
            raw_api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if raw_api_key != "":
                self.audit.openai_api_key = raw_api_key
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide cached settings."""

    return Settings()
