"""Synthesizer Agent for Composite Typed Responses, Figure Provenance, and Numerical Grounding.

Specifications:
- Spec Phần II §6.4 (Answer & Figure contracts)
- TC-T3-13: Strict Figure provenance checking against execution logs
- M-08 = 0%: Block ungrounded numbers, fallback to deterministic summary
- Review Focus #2: LangGraph node isolation
"""

from datetime import date
from typing import Any, Callable

from app.agents.explainer import format_metric_value
from app.agents.grounding import verify_numerical_grounding
from app.agents.llm_text import TextLLMClient, create_text_llm_client
from app.agents.models import Advice, Answer, Explanation, Figure, Source, Trend
from app.core.config import Settings, get_settings
from app.knowledge.loader import get_kpi
from app.orchestration.state import ChatState


def verify_figure_provenance(
    figures: list[Figure],
    valid_query_ids: set[str],
) -> tuple[list[Figure], list[str]]:
    """Verify that every Figure's source_query_id exists in execution logs.

    TC-T3-13: Figures referencing fake/unexecuted query IDs (e.g. 'sql-fake999')
    are stripped and 'UNVERIFIED_FIGURE_STRIPPED' is added to warnings.
    """
    verified: list[Figure] = []
    warnings: list[str] = []

    for fig in figures:
        if fig.source_query_id in valid_query_ids:
            verified.append(fig)
        else:
            warnings.append("UNVERIFIED_FIGURE_STRIPPED")

    return verified, warnings


def run_synthesizer(
    state: ChatState,
    llm_client: TextLLMClient | None = None,
    settings: Settings | None = None,
) -> tuple[Answer, list[str]]:
    """Execute response synthesis, strictly validating figures, sources, and numerical grounding."""
    request_id = state.get("request_id") or "req-default"
    sql_state = state.get("sql") or {}
    rag_state = state.get("rag") or {}
    explanation_state = state.get("explanation") or {}
    trend_state = state.get("trend") or {}
    advice_list = state.get("advice") or []
    data_profile = state.get("data_profile", "real")
    kpi_keys = state.get("kpi_keys") or []
    synth_warnings: list[str] = []
    intent = state.get("intent")
    errors = state.get("errors") or []
    warnings = list(dict.fromkeys(state.get("warnings") or []))

    # Case 1: Blocked intent (TC-T4-04)
    if intent == "blocked":
        refusal_reason = errors[0] if errors else "Yêu cầu bị từ chối do vi phạm an toàn hoặc phân quyền."
        answer = Answer(
            summary=f"Yêu cầu bị từ chối: {refusal_reason}",
            figures=[],
            explanation=None,
            trend=None,
            advice=[],
            sql=None,
            sources=[],
            confidence=0.0,
            warnings=warnings,
            request_id=request_id,
        )
        return answer, warnings

    # Case 2: Alert intent
    if intent == "alert":
        alerts = state.get("alerts") or []
        if not alerts:
            summary = "Hiện tại không ghi nhận cảnh báo nào chưa được xử lý trên hệ thống."
        else:
            alert_lines = [
                f"- [{a.get('severity', 'canh_bao').upper()}] {a.get('message', '')} "
                f"(KPI: {a.get('kpi_key', 'N/A')}, Giá trị: {a.get('value', 'N/A')}, Ngưỡng: {a.get('threshold', 'N/A')})"
                for a in alerts
            ]
            summary = f"Hệ thống ghi nhận {len(alerts)} cảnh báo chưa xử lý:\n" + "\n".join(alert_lines)
        answer = Answer(
            summary=summary,
            figures=[],
            explanation=None,
            trend=None,
            advice=[],
            sql=None,
            sources=[],
            confidence=0.90,
            warnings=warnings,
            request_id=request_id,
        )
        return answer, warnings

    # Step 1: Collect valid query IDs from execution logs
    valid_query_ids: set[str] = set()
    if sql_state.get("source_query_id"):
        valid_query_ids.add(sql_state["source_query_id"])
    if trend_state.get("source_query_id"):
        valid_query_ids.add(trend_state["source_query_id"])
    for tr in state.get("trace") or []:
        if isinstance(tr, dict) and tr.get("source_query_id"):
            valid_query_ids.add(tr["source_query_id"])

    # Step 2: Extract candidate figures from SQL result rows
    candidate_figures: list[Figure] = []
    if sql_state.get("status") == "ok":
        rows = sql_state.get("rows") or []
        if isinstance(rows, list) and rows:
            first_row = rows[0]
            if isinstance(first_row, dict):
                for col, val in first_row.items():
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        name = col
                        unit = ""
                        try:
                            kpi_def = get_kpi(col)
                            name = kpi_def.ten
                            unit = kpi_def.don_vi
                        except Exception:
                            if kpi_keys:
                                try:
                                    kpi_def = get_kpi(kpi_keys[0])
                                    name = kpi_def.ten
                                    unit = kpi_def.don_vi
                                except Exception:
                                    name = col.replace("_", " ").title()
                            else:
                                name = col.replace("_", " ").title()

                        as_of = date(2026, 7, 31) if data_profile == "real" else date.today()
                        candidate_figures.append(
                            Figure(
                                name=name,
                                value=float(val),
                                unit=unit,
                                as_of=as_of,
                                source_query_id=sql_state.get("source_query_id") or "",
                            )
                        )

    # Step 3: Verify provenance (TC-T3-13)
    verified_figures, prov_warnings = verify_figure_provenance(
        figures=candidate_figures,
        valid_query_ids=valid_query_ids,
    )

    # Step 4: Validate sub-agent models
    explanation_obj: Explanation | None = None
    if explanation_state and explanation_state.get("kpi_key"):
        try:
            explanation_obj = Explanation.model_validate(explanation_state)
        except Exception:
            explanation_obj = None

    trend_obj: Trend | None = None
    if trend_state and trend_state.get("kpi_key"):
        try:
            trend_obj = Trend.model_validate(trend_state)
        except Exception:
            trend_obj = None

    advice_objs: list[Advice] = []
    for a in advice_list:
        try:
            advice_objs.append(Advice.model_validate(a))
        except Exception:
            continue

    source_objs: list[Source] = []
    for s in rag_state.get("sources", []):
        try:
            source_objs.append(Source.model_validate(s))
        except Exception:
            continue

    sql_str = sql_state.get("sql")

    # Determine confidence
    if sql_state:
        confidence = float(sql_state.get("confidence", 0.0))
    elif rag_state.get("grounding_ok"):
        confidence = 0.85
    else:
        confidence = 0.0

    if state.get("needs_clarification"):
        confidence = 0.0

    # Step 5: Construct deterministic summary (as fallback or primary)
    cutoff_notice = "chốt ngày 31/07/2026" if data_profile == "real" else "dữ liệu mô phỏng synth"

    row_text_items: list[str] = []
    if sql_state.get("status") == "ok":
        rows = sql_state.get("rows") or []
        if isinstance(rows, list) and rows:
            first_r = rows[0]
            if isinstance(first_r, dict):
                for col, val in first_r.items():
                    if isinstance(val, str) and val.strip() and col not in ("record_type", "rn", "account_no", "item_code", "as_of_date"):
                        row_text_items.append(f"{col.replace('_', ' ').title()}: {val}")

    if verified_figures:
        fig_texts = [f"{f.name}: {format_metric_value(f.value, f.unit)}" for f in verified_figures]
        all_parts = row_text_items + fig_texts
        summary_core = f"Theo số liệu từ hệ thống ({cutoff_notice}), " + ", ".join(all_parts) + "."
    elif row_text_items:
        summary_core = f"Theo số liệu từ hệ thống ({cutoff_notice}), " + ", ".join(row_text_items) + "."
    elif rag_state.get("answer_text"):
        summary_core = rag_state["answer_text"]
    else:
        summary_core = "Không có số liệu phù hợp với truy vấn."

    if rag_state.get("answer_text") and verified_figures:
        det_summary = f"{summary_core}\n\n{rag_state['answer_text']}"
    else:
        det_summary = summary_core

    # Step 6: LLM Summary Synthesis with Numerical Grounding Check (M-08)
    summary = det_summary
    if llm_client is not None:
        allowed_values: list[float] = [f.value for f in verified_figures]
        if explanation_obj:
            allowed_values.extend(explanation_obj.grounded_values)
        if trend_obj:
            allowed_values.extend([p.value for p in trend_obj.series])
        for r in sql_state.get("rows", []):
            if isinstance(r, dict):
                for v in r.values():
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        allowed_values.append(float(v))

        prompt = (
            f"Tóm tắt kết quả phân tích tài chính ({cutoff_notice}):\n"
            f"Số liệu: {', '.join([f'{f.name}={f.value}' for f in verified_figures])}\n"
            f"Thông tin bổ sung: {det_summary}"
        )
        try:
            llm_text = llm_client.generate_text(
                system_prompt="Bạn là trợ lý AI phân tích tài chính Gỗ Minh Long. Tóm tắt trung thực, tuyệt đối không bịa số.",
                user_prompt=prompt,
            )
            # Numerical grounding verification guard (M-08 = 0%)
            verdict = verify_numerical_grounding(text=llm_text, allowed_values=allowed_values)
            if verdict.ok:
                summary = llm_text
                if data_profile == "real" and verified_figures and "31/07/2026" not in summary:
                    summary = f"Theo số liệu kế toán chốt ngày 31/07/2026: {summary}"
            else:
                synth_warnings.append("UNGROUNDED_NUMBER")
                summary = det_summary
        except Exception:
            summary = det_summary

    # Deduplicate warnings preserving insertion order (Review rule)
    all_warnings = list(
        dict.fromkeys(
            list(state.get("warnings") or []) + prov_warnings + synth_warnings
        )
    )

    answer = Answer(
        summary=summary,
        figures=verified_figures,
        explanation=explanation_obj,
        trend=trend_obj,
        advice=advice_objs,
        sql=sql_str,
        sources=source_objs,
        confidence=confidence,
        warnings=all_warnings,
        request_id=request_id,
    )

    return answer, all_warnings


def create_synthesize_node(
    llm_client: TextLLMClient | None = None,
    settings: Settings | None = None,
) -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph node function for synthesize."""

    def synthesize_node(state: ChatState) -> dict[str, Any]:
        answer, warnings = run_synthesizer(
            state=state,
            llm_client=llm_client,
            settings=settings,
        )
        return {
            "answer": answer.model_dump(),
            "warnings": warnings,
            "trace": [
                {
                    "node": "synthesize",
                    "confidence": answer.confidence,
                    "figures_count": len(answer.figures),
                    "sources_count": len(answer.sources),
                }
            ],
        }

    return synthesize_node


def create_clarify_node(
    settings: Settings | None = None,
) -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph node function for clarify when data is missing or confidence is low."""

    def clarify_node(state: ChatState) -> dict[str, Any]:
        errors = state.get("errors") or []
        warnings = list(dict.fromkeys(state.get("warnings") or []))
        reason = " / ".join(errors) if errors else "Yêu cầu cần làm rõ thêm thông tin hoặc không tìm thấy nguồn dữ liệu phù hợp."

        answer = Answer(
            summary=f"Cần làm rõ thông tin: {reason}",
            figures=[],
            explanation=None,
            trend=None,
            advice=[],
            sql=(state.get("sql") or {}).get("sql"),
            sources=[],
            confidence=0.0,
            warnings=warnings,
            request_id=state.get("request_id") or "req-clarify",
        )

        return {
            "answer": answer.model_dump(),
            "needs_clarification": True,
            "trace": [{"node": "clarify", "reason": reason}],
        }

    return clarify_node
