"""HTTP DTOs for WorkAI FastAPI layer."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    """Error payload body."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Unified API error response."""

    error: ErrorBody


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: str
    service: str


class DeepHealthResponse(BaseModel):
    """Deep health payload with DB checks."""

    status: str
    service: str
    version: str
    db_ok: bool
    alembic_version: str | None


class RawTaskDTO(BaseModel):
    """raw_tasks projection for API."""

    raw_task_id: int
    spreadsheet_id: str
    sheet_title: str
    row_idx: int
    col_idx: int
    cell_a1: str
    cell_ingested_at: datetime
    employee_name_raw: str | None
    work_date: date | None
    line_no: int
    line_text: str
    parsed_at: datetime


class NormalizedTaskDTO(BaseModel):
    """tasks_normalized projection for API."""

    id: int
    raw_task_id: int | None
    employee_id: int
    task_date: date
    canonical_text: str
    duration_minutes: int | None
    task_category: str | None
    time_source: str
    is_smart: bool
    is_micro: bool
    result_confirmed: bool
    is_zhdun: bool
    normalized_at: datetime
    spreadsheet_id: str
    sheet_title: str
    row_idx: int
    col_idx: int
    line_no: int


class OperationalCycleDTO(BaseModel):
    """operational_cycles projection for API."""

    id: int
    employee_id: int
    task_date: date
    cycle_key: str
    canonical_text: str
    task_category: str
    total_duration_minutes: int
    tasks_count: int
    is_zhdun: bool
    avg_quality_score: float | None
    avg_smart_score: float | None
    created_at: datetime


class AnalysisStartRequest(BaseModel):
    """Start audit request body."""

    employee_id: int = Field(gt=0)
    task_date: date
    force: bool = False


class AnalysisStartResponse(BaseModel):
    """Start audit response body."""

    run_id: UUID
    employee_id: int
    task_date: date
    status: str
    cached: bool
    report_json: dict[str, object]


class AuditRunStatusDTO(BaseModel):
    """Audit run status payload."""

    id: UUID
    employee_id: int
    task_date: date
    status: str
    started_at: datetime
    finished_at: datetime | None
    report_json: dict[str, object] | None
    error: str | None
    forced: bool


class AuditHistoryItemDTO(BaseModel):
    """Audit history row payload."""

    id: UUID
    employee_id: int
    task_date: date
    status: str
    started_at: datetime
    finished_at: datetime | None
    forced: bool


class FeedbackRequest(BaseModel):
    """Feedback body for one audit run."""

    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    submitted_by: str | None = Field(default=None, max_length=255)


class FeedbackResponse(BaseModel):
    """Feedback write response."""

    run_id: UUID
    status: str


class TeamOverviewRowDTO(BaseModel):
    """Team overview row."""

    employee_id: int
    task_date: date
    ghost_minutes: int
    ghost_hours: float
    index_of_trust_base: float
    tasks_count: int
    cycles_count: int


class DebugLogRowDTO(BaseModel):
    """Unified debug log row (pipeline_errors or audit failure)."""

    source: str
    created_at: datetime
    phase: str
    run_id: str | None
    source_ref: str
    error_type: str
    error_message: str


class DebugCostRowDTO(BaseModel):
    """audit_cost_daily row."""

    rollup_date: date
    runs_count: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    rollup_at: datetime


class ListEnvelope(BaseModel):
    """Simple generic-ish list envelope."""

    model_config = ConfigDict(extra="forbid")

    items: list[object]
