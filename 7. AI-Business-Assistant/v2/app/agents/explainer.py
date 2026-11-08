"""Explainer Agent for business KPI narrative generation and numerical hallucination defense.

Specifications:
- Spec Phần II §6 (Agent Architecture)
- TC-T3-08 & M-08 (Zero Hallucinated Numbers Gate)
- Review Focus #1: Whitelisted identifiers extracted from KPI formula and components
- Review Focus #2: LangGraph node isolation (writes strictly explanation, warnings, trace, and optionally errors)
"""

import re
from typing import Any, Callable

from app.agents.grounding import verify_numerical_grounding
from app.agents.llm_text import TextLLMClient, create_text_llm_client
from app.agents.models import Explanation
from app.knowledge.loader import get_kpi
from app.knowledge.models import KpiDefinition
from app.orchestration.state import ChatState


def extract_kpi_whitelisted_identifiers(kpi_def: KpiDefinition) -> set[str]:
    """Extract account numbers and code identifiers from KPI formula and components."""
    identifiers: set[str] = set()

    # Digits from formula (e.g. 34111, 34113, 34114 in account_no LIKE '34111%')
    formula_digits = re.findall(r"\b\d{3,6}\b", kpi_def.cong_thuc)
    identifiers.update(formula_digits)

    # Quoted string tokens from formula
    quoted_tokens = re.findall(r"'([^']+)'", kpi_def.cong_thuc)
    for q in quoted_tokens:
        clean_q = q.strip("%")
        if clean_q.isdigit():
            identifiers.add(clean_q)

    # Identifiers from components
    for comp in kpi_def.thanh_phan:
        comp_digits = re.findall(r"\b\d{3,6}\b", comp)
        identifiers.update(comp_digits)

    return identifiers


def extract_kpi_threshold_values(kpi_def: KpiDefinition) -> list[float]:
    """Extract numeric threshold values from KPI thresholds definition."""
    thresholds: list[float] = []
    if not kpi_def.nguong:
        return thresholds

    for val in kpi_def.nguong.values():
        val_str = str(val)
        matches = re.findall(r"\d+(?:[.,]\d+)?", val_str)
        for m in matches:
            try:
                num = float(m.replace(",", "."))
                thresholds.append(num)
                # If threshold is in ratio [0, 1], also allow percentage [0, 100]
                if 0.0 <= num <= 1.0:
                    thresholds.append(num * 100.0)
                elif num > 1.0:
                    thresholds.append(num / 100.0)
            except ValueError:
                continue

    return thresholds


def format_metric_value(val: float | None, unit: str) -> str:
    """Format numeric KPI value with unit for narrative presentation."""
    if val is None:
        return "Chưa có dữ liệu"

    if unit == "%":
        # Check if val is ratio (e.g. 0.9182) or percentage (91.82)
        pct_val = val * 100.0 if abs(val) <= 1.0 else val
        return f"{pct_val:.2f}%"

    if unit.upper() in ["VND", "VNĐ"]:
        if abs(val) >= 1e9:
            val_in_billions = val / 1e9
            formatted_int = f"{val:,.0f}".replace(",", ".")
            return f"{formatted_int} VNĐ (xấp xỉ {val_in_billions:,.2f} tỷ VNĐ)".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        formatted_int = f"{val:,.0f}".replace(",", ".")
        return f"{formatted_int} VNĐ"

    return f"{val} {unit}"


def run_explainer(
    kpi_keys: list[str],
    sql_state: dict[str, Any] | None = None,
    llm_client: TextLLMClient | None = None,
) -> tuple[Explanation | None, list[str]]:
    """Generate business explanation for KPI with strict numerical grounding verification.

    TC-T3-08: If the LLM invents any ungrounded numbers (e.g. '850 tỷ'), the narrative
    is rejected and falls back to the deterministic template narrative from kpi_definitions.yaml,
    and 'UNGROUNDED_NUMBER' is attached to warnings.
    """
    if not kpi_keys:
        return None, []

    primary_key = kpi_keys[0]
    try:
        kpi_def = get_kpi(primary_key)
    except KeyError:
        return None, [f"KPI key '{primary_key}' not found in knowledge base"]

    # Step 1: Collect allowed values from SQL result rows and KPI thresholds
    allowed_values: list[float] = []
    primary_sql_val: float | None = None
    source_query_id: str | None = None

    if sql_state:
        source_query_id = sql_state.get("source_query_id")
        rows = sql_state.get("rows", [])
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    # Find value matching kpi_key
                    if primary_key in row and isinstance(row[primary_key], (int, float)):
                        primary_sql_val = float(row[primary_key])

                    for v in row.values():
                        if isinstance(v, (int, float)) and not isinstance(v, bool):
                            f_val = float(v)
                            allowed_values.append(f_val)
                            if primary_sql_val is None:
                                primary_sql_val = f_val

    # Include threshold numbers (e.g. 0.70, 0.90, 70, 90)
    allowed_values.extend(extract_kpi_threshold_values(kpi_def))

    # Step 2: Collect whitelisted identifiers from KPI definition
    whitelisted_ids = extract_kpi_whitelisted_identifiers(kpi_def)

    # Step 3: Build deterministic template narrative as safe fallback
    formatted_val = format_metric_value(primary_sql_val, kpi_def.don_vi)
    deterministic_narrative = (
        f"{kpi_def.ten} ({kpi_def.key}): {kpi_def.y_nghia}. "
        f"Công thức tính: {kpi_def.cong_thuc}. "
        f"Giá trị ghi nhận: {formatted_val}."
    )

    # Step 4: Synthesize narrative via TextLLMClient
    client = llm_client
    if client is None:
        client, _ = create_text_llm_client("auto")

    system_prompt = (
        "Bạn là chuyên gia phân tích tài chính doanh nghiệp Công ty Gỗ Minh Long.\n"
        "Hãy giải thích ngắn gọn, súc tích chỉ số KPI theo công thức và số liệu thực tế được cung cấp.\n"
        "QUY TẮC BẮT BUỘC:\n"
        "- Chỉ sử dụng các con số có trong dữ liệu thực tế hoặc ngưỡng công thức.\n"
        "- Tuyệt đối không tự bịa đặt, phỏng đoán hoặc đưa thêm bất kỳ con số nào khác vào câu trả lời."
    )
    user_prompt = (
        f"Chỉ số: {kpi_def.ten} ({kpi_def.key})\n"
        f"Công thức: {kpi_def.cong_thuc}\n"
        f"Ý nghĩa: {kpi_def.y_nghia}\n"
        f"Dữ liệu thực tế: {formatted_val}\n\n"
        "Hãy viết đoạn giải thích ngắn gọn:"
    )

    warnings: list[str] = []
    try:
        llm_narrative = client.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)
    except Exception:
        llm_narrative = deterministic_narrative

    # Step 5: Numerical Grounding Verification Guard (TC-T3-08 & M-08)
    verdict = verify_numerical_grounding(
        text=llm_narrative,
        allowed_values=allowed_values,
        whitelisted_identifiers=whitelisted_ids,
    )

    if verdict.ok:
        narrative = llm_narrative
    else:
        # Ungrounded hallucination detected! Reject LLM text and fall back to template
        narrative = deterministic_narrative
        warnings.append("UNGROUNDED_NUMBER")

    explanation = Explanation(
        kpi_key=primary_key,
        ten=kpi_def.ten,
        cong_thuc=kpi_def.cong_thuc,
        thanh_phan=kpi_def.thanh_phan,
        y_nghia=kpi_def.y_nghia,
        narrative=narrative,
        grounded_values=[v for v in allowed_values if isinstance(v, (int, float))],
        source_query_id=source_query_id,
    )

    return explanation, warnings


def create_explain_node(
    llm_client: TextLLMClient | None = None,
) -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph node function for explain.

    Review Focus #2: Node writes ONLY a subset of {'explanation', 'warnings', 'trace', 'errors'}.
    """

    def explain_node(state: ChatState) -> dict[str, Any]:
        kpi_keys = state.get("kpi_keys", [])
        sql_state = state.get("sql")

        explanation, warnings = run_explainer(
            kpi_keys=kpi_keys,
            sql_state=sql_state,
            llm_client=llm_client,
        )

        updates: dict[str, Any] = {
            "explanation": explanation.model_dump() if explanation else {},
            "warnings": warnings,
            "trace": [
                {
                    "node": "explain",
                    "kpi_keys": kpi_keys,
                    "explanation_present": explanation is not None,
                }
            ],
        }
        return updates

    return explain_node
