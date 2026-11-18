"""Pydantic request and response schemas for FastAPI endpoints.

Specifications:
- Spec §5 T5 (API Gateway Schemas)
- Unified Error Envelope: {"error": {"code": str, "message": str, "request_id": str}}
"""

from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


# ==============================================================================
# Unified Error Schemas
# ==============================================================================

class ApiErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ApiErrorResponse(BaseModel):
    error: ApiErrorDetail


# ==============================================================================
# Chat Schemas
# ==============================================================================

class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    data_profile: Literal["real", "synth"] | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    request_id: str
    standalone_query: str | None = None
    intent: str | None = None
    data_profile: str = "real"
    trace: list[dict[str, Any]] = Field(default_factory=list)
    kpi_keys: list[str] = Field(default_factory=list)


# ==============================================================================
# KPI Schemas
# ==============================================================================

class KpiValueResponse(BaseModel):
    kpi_key: str
    kpi_name: str
    value: float
    unit: str
    as_of_date: str
    data_profile: str
    sql_executed: str
    warnings: list[str] = Field(default_factory=list)
    cached: bool = False
    series: list[dict[str, Any]] | None = None
    previous_value: float | None = None
    delta_pct: float | None = None
    series_warning: str | None = None


# ==============================================================================
# Alert Schemas
# ==============================================================================

class AlertItem(BaseModel):
    id: int
    rule_id: str | None = None
    kpi_key: str
    severity: str = "warning"
    alert_level: str = "warning"
    message: str
    current_value: float | None = None
    threshold_value: float | None = None
    value: float | None = None
    threshold: float | None = None
    is_acknowledged: bool = False
    created_at: str | datetime
    acknowledged_at: str | datetime | None = None
    acknowledged_by: str | None = None
    period: str | None = None
    evidence: dict[str, Any] | None = None
    domain: str | None = None
    escalated_at: str | None = None
    occurrence_count: int = 1


class AlertListResponse(BaseModel):
    alerts: list[AlertItem]
    total: int
    warnings: list[str] = Field(default_factory=list)


class AlertAckResponse(BaseModel):
    id: int
    is_acknowledged: bool
    acknowledged_by: str
    acknowledged_at: str | datetime


# ==============================================================================
# Feedback Schemas
# ==============================================================================

class FeedbackRequest(BaseModel):
    request_id: str
    rating: Literal["up", "down"]
    session_id: str | None = None
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: int | None = None
    status: str = "ok"
    message: str = "Feedback recorded"


# ==============================================================================
# History Schemas
# ==============================================================================

class HistoryTurnItem(BaseModel):
    turn_id: int | str
    session_id: str
    query: str
    answer_summary: str | None = None
    intent: str | None = None
    created_at: str | datetime


class HistoryListResponse(BaseModel):
    turns: list[HistoryTurnItem]
    total: int


class HistoryDeleteResponse(BaseModel):
    deleted_count: int
    status: str = "ok"


# ==============================================================================
# Health & Readiness Schemas
# ==============================================================================

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"


class ReadyResponse(BaseModel):
    status: str
    db: str
    profile: str
    details: dict[str, Any] = Field(default_factory=dict)
    error: ApiErrorDetail | None = None


# ==============================================================================
# Action Schemas
# ==============================================================================

class ActionCreateRequest(BaseModel):
    source_type: Literal["alert", "chat"]
    source_ref: str
    kpi_key: str
    level: Literal["canh_bao", "nghiem_trong"]
    title: str
    due_date: date | None = None
    note: str | None = Field(default=None, max_length=1000)


class ActionItem(BaseModel):
    id: int
    title: str
    kpi_key: str
    level: str
    domain: str
    source_type: str
    source_ref: str
    assigned_role: str
    status: str
    due_date: date | None = None
    note: str | None = None
    created_by: str
    created_at: str | datetime
    updated_at: str | datetime
    warnings: list[str] = Field(default_factory=list)


class ActionListResponse(BaseModel):
    actions: list[ActionItem]
    total: int
    warnings: list[str] = Field(default_factory=list)


class ActionUpdateRequest(BaseModel):
    status: Literal["open", "in_progress", "done", "dismissed"] | None = None
    note: str | None = Field(default=None, max_length=1000)


# ==============================================================================
# Pin Schemas
# ==============================================================================

class PinRequest(BaseModel):
    kpi_key: str


class PinItem(BaseModel):
    kpi_key: str
    position: int
    created_at: str | datetime
    warnings: list[str] = Field(default_factory=list)


class PinListResponse(BaseModel):
    pins: list[PinItem]
    total: int
    warnings: list[str] = Field(default_factory=list)


class PinDeleteResponse(BaseModel):
    deleted: int
    warnings: list[str] = Field(default_factory=list)


# ==============================================================================
# Overview Schemas
# ==============================================================================

class OverviewKpiCard(BaseModel):
    kpi_key: str
    kpi_name: str | None = None
    unit: str | None = None
    domain: str
    value: float | None = None
    previous_value: float | None = None
    delta_pct: float | None = None
    series: list[dict[str, Any]] = Field(default_factory=list)
    pinned: bool = False
    error: str | None = None
    series_warning: str | None = None


class OverviewResponse(BaseModel):
    greeting_title: str
    data_profile: str
    as_of_date: str
    last_alert_job_at: str | None = None
    open_alerts: dict[str, int] = Field(default_factory=dict)
    open_actions: int = 0
    kpis: list[OverviewKpiCard] = Field(default_factory=list)
    top_alerts: list[AlertItem] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)



