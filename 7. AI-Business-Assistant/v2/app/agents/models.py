"""Typed Agent Output Models.

Specifications:
- Spec Phần II §6.4 (Agent Output Contracts: Source, Explanation, Trend, Advice, Figure, Answer, GroundingVerdict)
- Review Focus #1: Strict typing and disclaimer validation for business advice
"""

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Source(BaseModel):
    """Citation source representing a retrieved document chunk."""

    citation_id: int
    source: str
    heading_path: str
    snippet: str
    score: float = 0.0


class Explanation(BaseModel):
    """Business explanation of a KPI formula, components, meaning, and values."""

    kpi_key: str
    ten: str
    cong_thuc: str
    thanh_phan: list[str] = Field(default_factory=list)
    y_nghia: str
    narrative: str
    grounded_values: list[float] = Field(default_factory=list)
    source_query_id: str | None = None


class TrendPoint(BaseModel):
    """Single period data point for time-series trend analysis."""

    period: str
    value: float


class TrendAnomaly(BaseModel):
    """Detected anomaly in time-series trend data."""

    period: str
    value: float
    severity: Literal["canh_bao", "nghiem_trong"]
    reason: str
    mom_growth: float | None = None


class Trend(BaseModel):
    """Structured trend analysis output over historical periods."""

    kpi_key: str
    data_coverage: int
    series: list[TrendPoint] = Field(default_factory=list)
    mom_growth: float | None = None
    yoy_growth: float | None = None
    anomalies: list[TrendAnomaly] = Field(default_factory=list)
    summary_text: str = ""
    source_query_id: str


class Advice(BaseModel):
    """Actionable recommendations derived from business rules with mandated disclaimer."""

    kpi_key: str
    level: Literal["canh_bao", "nghiem_trong"]
    actions: list[str]
    authority_role: str
    disclaimer: str = "Gợi ý tham khảo từ quy tắc nghiệp vụ, cần người có thẩm quyền quyết định"

    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer(cls, v: str) -> str:
        if "cần người có thẩm quyền quyết định" not in v:
            raise ValueError("disclaimer must contain 'cần người có thẩm quyền quyết định'")
        return v


class Figure(BaseModel):
    """Primary quantitative metric figure extracted from query result."""

    name: str
    value: float
    unit: str
    as_of: date
    source_query_id: str


class Answer(BaseModel):
    """Comprehensive composite response contract returned to the user."""

    summary: str
    figures: list[Figure] = Field(default_factory=list)
    explanation: Explanation | None = None
    trend: Trend | None = None
    advice: list[Advice] = Field(default_factory=list)
    sql: str | None = None
    sources: list[Source] = Field(default_factory=list)
    confidence: float
    warnings: list[str] = Field(default_factory=list)
    request_id: str


class GroundingVerdict(BaseModel):
    """Result of numerical grounding verification on text against allowed figures."""

    ok: bool
    ungrounded_tokens: list[str] = Field(default_factory=list)
