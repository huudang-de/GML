"""Pydantic Models for T2 Semantic Knowledge Layer.

Specifications:
- Spec §5 T2 (Semantic Knowledge Layer)
- Spec §6.9 (Benchmark 60 câu)
- Spec §11.10 (Data Leakage Safeguards)
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


class KpiDefinition(BaseModel):
    """Specification of a Business KPI across the 5 BRD dashboards."""

    key: str
    ten: str
    dashboard: str  # D1, D2, D3, D4, D5
    don_vi: str  # VND, %, SKU, Hợp đồng, etc.
    cong_thuc: str
    nguon_view: list[str]
    golden_ref: str
    thanh_phan: list[str] = Field(default_factory=list)
    y_nghia: str
    plausible_range: tuple[float, float] | None = None
    nguong: dict[str, str] = Field(default_factory=dict)
    data_caveat: str | None = None


class BusinessRuleAction(BaseModel):
    """Approved operational recommendation and disclaimer for a KPI threshold condition."""

    actions: list[str]
    authority_role: str
    disclaimer: str = "Gợi ý tham khảo từ quy tắc nghiệp vụ, cần người có thẩm quyền quyết định"


class GoldenQuery(BaseModel):
    """Ground-truth SQL query and expected scalar / checksum from UAT."""

    id: str
    kpi_key: str | None = None
    dashboard: str
    question_vi: str
    paraphrases: list[str] = Field(default_factory=list)
    sql_file: str
    sql_text: str = ""
    views_used: list[str]
    split: Literal["dev"] = "dev"
    uat_expected: float
    value_column: str | None = None
    tolerance: float = 1e-4


class GoldenMatch(BaseModel):
    """Match result returned by semantic TF-IDF matcher with similarity score."""

    query: GoldenQuery
    similarity: float


class BenchmarkExpectation(BaseModel):
    """Expected evaluation metrics for a benchmark item."""

    gia_tri: float | None = None
    dung_sai_tuong_doi: float = 1e-4
    so_dong: int | None = None


class BenchmarkItem(BaseModel):
    """Single benchmark evaluation test case."""

    id: str
    loai: Literal["sql", "rag", "both", "follow_up", "ngoai_pham_vi", "an_toan"]
    do_kho: Literal["de", "vua", "kho"] = "vua"
    dashboard: str | None = None
    split: Literal["dev", "test"]
    profile: Literal["real", "synth"] = "real"
    role: str = "ceo"
    cau_hoi: str
    reference_sql: str | None = None
    expected_status: Literal["ok", "no_data", "rejected", "blocked"] = "ok"
    ky_vong: BenchmarkExpectation | None = None
    expected_source: str | None = None
    reviewed_by: str
    reviewed_at: str
