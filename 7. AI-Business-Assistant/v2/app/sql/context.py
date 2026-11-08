"""Context retrieval and prompt assembly for Text-to-SQL generation.

Specifications:
- Spec §5 T3 (6-step SQLAgent, Step 1: Context Retrieval)
- Review Focus #1: Role-based view filtering strictly before LLM call
- C1 Data Caveats: Missing COGS (B02-DN_11=0), Interest (B02-DN_23=0), Single-month revenue (07/2026)
"""

from datetime import date
from pathlib import Path
import re
from typing import Optional, Set
import unicodedata

from pydantic import BaseModel, Field

from app.core.security import get_allowed_views, load_catalog
from app.knowledge.loader import load_kpis, match_golden
from app.knowledge.models import GoldenMatch, KpiDefinition


class SqlPromptContext(BaseModel):
    """Encapsulates all metadata and knowledge required to generate and validate SQL."""

    question: str
    role: str
    data_profile: str
    as_of_date: date
    allowed_views: Set[str] = Field(default_factory=set)
    catalog_markdown: str = ""
    golden_matches: list[GoldenMatch] = Field(default_factory=list)
    matched_kpis: list[KpiDefinition] = Field(default_factory=list)
    c1_caveats: list[str] = Field(default_factory=list)
    known_missing_data_reason: str | None = None


DEFAULT_C1_CAVEATS: list[str] = [
    "AS_OF_DATE = 2026-07-31: Toàn bộ số liệu chốt sổ kế toán tại ngày 31/07/2026. Tháng 8/2026 chưa khoá sổ nên không có dữ liệu chốt.",
    "B02-DN_11 = 0: Giá vốn hàng bán trên BCTC chưa có dữ liệu thực tế (bằng 0). Không tính biên lợi nhuận gộp 100%.",
    "B02-DN_23 = 0: Chi phí lãi vay trên BCTC chưa có dữ liệu thực tế (bằng 0).",
    "Doanh thu trên profile real chỉ có số liệu phát sinh của tháng 07/2026 (không có dữ liệu T1-T6/2026 và năm 2025).",
]


def _strip_accents(text: str) -> str:
    """Normalize and strip accents for keyword matching."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFC", text).lower()


def detect_known_c1_missing_data(question: str, data_profile: str = "real") -> str | None:
    """Detect if a question falls into known C1 missing data gaps on real warehouse."""
    if data_profile != "real":
        return None

    q_norm = _strip_accents(question)

    # 1. Gross margin (biên lợi nhuận gộp)
    if "bien loi nhuan gop" in q_norm or "gross margin" in q_norm:
        return "B02-DN_11 = 0: Giá vốn hàng bán chưa nạp trên dữ liệu thật, không thể tính biên lợi nhuận gộp."

    # 2. COGS (giá vốn hàng bán)
    if ("gia von" in q_norm or "cogs" in q_norm or "b02-dn_11" in q_norm) and "ton kho" not in q_norm:
        return "B02-DN_11 = 0: Giá vốn hàng bán phát sinh trong kỳ chưa có dữ liệu trên hồ sơ thật."

    # 3. YoY revenue comparison / 2025 revenue
    if ("yoy" in q_norm or "cung ky" in q_norm or "nam 2025" in q_norm or "2025" in q_norm) and ("doanh thu" in q_norm or "tang truong" in q_norm):
        return "Dữ liệu thật chưa có số liệu doanh thu năm 2025 để tính tăng trưởng cùng kỳ (YoY)."

    # 4. Revenue for months 1-6 (T1-T6 / tháng 1 -> tháng 6)
    if "doanh thu" in q_norm:
        for month in ["thang 1 ", "thang 2 ", "thang 3 ", "thang 4 ", "thang 5 ", "thang 6 ", "thang 01", "thang 02", "thang 03", "thang 04", "thang 05", "thang 06", "t1", "t2", "t3", "t4", "t5", "t6", "quy 1", "quy 2"]:
            # Check if mentions specific month other than month 7
            if re.search(r"\b" + re.escape(month.strip()) + r"\b", q_norm) and "thang 7" not in q_norm and "thang 07" not in q_norm:
                return "Dữ liệu doanh thu trên profile real chỉ có tháng 07/2026, các tháng 1-6/2026 chưa có số liệu."

    return None


def format_catalog_markdown(catalog: dict, allowed_views: Set[str]) -> str:
    """Format markdown documentation of allowed views for LLM prompt context."""
    if not allowed_views:
        return ""

    views_dict = catalog.get("views", {})
    md_lines: list[str] = [
        "## Danh mục Views được phép truy vấn trong schema `ai_views`",
        "",
    ]

    for view_name in sorted(allowed_views):
        if view_name not in views_dict:
            continue
        vmeta = views_dict[view_name]
        md_lines.append(f"### View: `ai_views.{view_name}`")
        if vmeta.get("description"):
            md_lines.append(f"**Mô tả:** {vmeta['description']}")
        if vmeta.get("grain"):
            md_lines.append(f"**Hạt dữ liệu:** {vmeta['grain']}")
        md_lines.append("**Các cột:**")
        for col in vmeta.get("columns", []):
            unit_str = f" ({col['unit']})" if col.get("unit") else ""
            desc = col.get("description", "")
            md_lines.append(f"- `{col['name']}` ({col['type']}){unit_str}: {desc}")
        md_lines.append("")

    return "\n".join(md_lines)


def build_sql_prompt_context(
    question: str,
    role: str,
    data_profile: str = "real",
    as_of_date: date = date(2026, 7, 31),
    catalog_path: Optional[Path] = None,
) -> SqlPromptContext:
    """Build the complete SqlPromptContext strictly adhering to role-based access control.

    Review Focus #1:
    - Filters catalog and view descriptions strictly by get_allowed_views(role).
    - Unpermitted roles receive no catalog markdown and no golden queries with unpermitted views.
    - Matches top-3 Golden Queries.
    - Attaches matched KPI definitions whose views are within allowed_views.
    - Formulates C1 caveats and checks for known missing data.
    """
    allowed_views = get_allowed_views(role, catalog_path=catalog_path)
    catalog = load_catalog(catalog_path=catalog_path)

    # 1. Format catalog markdown strictly containing only permitted views
    catalog_md = format_catalog_markdown(catalog, allowed_views)

    # 2. Golden query matching (filtered strictly by role within match_golden)
    golden_matches = match_golden(question, role=role, k=3) if allowed_views else []

    # 3. Matched KPIs (only those permitted by allowed_views)
    all_kpis = load_kpis()
    matched_kpis: list[KpiDefinition] = []
    seen_kpi_keys: set[str] = set()

    # Extract KPI keys from golden matches
    for gm in golden_matches:
        if gm.query.kpi_key and gm.query.kpi_key in all_kpis:
            kpi_def = all_kpis[gm.query.kpi_key]
            if set(kpi_def.nguon_view).issubset(allowed_views):
                if kpi_def.key not in seen_kpi_keys:
                    matched_kpis.append(kpi_def)
                    seen_kpi_keys.add(kpi_def.key)

    # Search for additional KPIs mentioned in question
    q_norm = _strip_accents(question)
    for kpi_key, kpi_def in all_kpis.items():
        if kpi_key not in seen_kpi_keys and set(kpi_def.nguon_view).issubset(allowed_views):
            kpi_name_norm = _strip_accents(kpi_def.ten)
            if kpi_name_norm in q_norm or kpi_key in q_norm:
                matched_kpis.append(kpi_def)
                seen_kpi_keys.add(kpi_key)

    # 4. C1 caveats & missing data detection
    missing_reason = detect_known_c1_missing_data(question, data_profile=data_profile)

    return SqlPromptContext(
        question=question,
        role=role,
        data_profile=data_profile,
        as_of_date=as_of_date,
        allowed_views=allowed_views,
        catalog_markdown=catalog_md,
        golden_matches=golden_matches,
        matched_kpis=matched_kpis,
        c1_caveats=DEFAULT_C1_CAVEATS if data_profile == "real" else [],
        known_missing_data_reason=missing_reason,
    )
