"""Unit tests for SQLAgent node, RBAC filtering, and Graph integration.

Specifications:
- Spec §5 T3 (6-step SQLAgent, LangGraph Integration)
- Review Focus #1: Role-based allowed views filtering before LLM call
- Review Focus #4: Synthetic data warning badge attachment
- TC-T3-04: no_data skips synthesizer and routes to clarify
"""

from typing import Any
import pytest

from app.agents.sql_agent import (
    confidence_gate_node,
    create_sql_lookup_node,
    run_sql_pipeline,
)
from app.orchestration.graph import build_sql_graph
from app.orchestration.state import ChatState
from app.sql.context import build_sql_prompt_context
from app.sql.generator import MockSqlLLMClient
from app.sql.models import SqlDraft


def test_tc_t3_04_no_data_skips_synthesizer_in_graph():
    """TC-T3-04: Queries returning status='no_data' (or C1 out_of_scope) skip synthesizer and route to clarify."""
    synthesize_called = False
    clarify_called = False

    def spy_synthesize(state: ChatState) -> dict[str, Any]:
        nonlocal synthesize_called
        synthesize_called = True
        return {"answer": {"text": "Should not be called"}}

    def spy_clarify(state: ChatState) -> dict[str, Any]:
        nonlocal clarify_called
        clarify_called = True
        return {"answer": {"text": "Dữ liệu chưa có sẵn, xin làm rõ câu hỏi."}}

    mock_empty_client = MockSqlLLMClient(
        candidates=[
            SqlDraft(
                sql="SELECT * FROM ai_views.ai_v_bctc WHERE period_month = '2026-07' AND metric_code = 'B02-DN_11';",
                explanation_short="Kiểm tra giá vốn B02-DN_11",
                out_of_scope_reason="B02-DN_11 = 0: Giá vốn hàng bán chưa nạp trên dữ liệu thật",
            )
        ]
    )

    app = build_sql_graph(
        llm_client=mock_empty_client,
        node_overrides={
            "synthesize": spy_synthesize,
            "clarify": spy_clarify,
        },
    )

    final_state = app.invoke({
        "request_id": "req-tc-t3-04",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "Giá vốn hàng bán phát sinh trong kỳ tháng 7 năm 2026 là bao nhiêu tiền?",
        "data_profile": "real",
    })

    assert final_state.get("sql") is not None
    assert final_state["sql"]["status"] == "no_data"
    assert synthesize_called is False
    assert clarify_called is True
    assert final_state.get("needs_clarification") is True


def test_sql_agent_blocks_unpermitted_role_context():
    """Review Focus #1: RBAC strictly blocks unpermitted roles and scrubs view schema from prompt context."""
    llm_calls = 0

    def counting_generator(ctx, n=3):
        nonlocal llm_calls
        llm_calls += 1
        return [SqlDraft(sql="SELECT 1")]

    counting_client = MockSqlLLMClient(generator_fn=counting_generator)

    # 1. quan_tri_he_thong has 0 allowed views -> pipeline rejects immediately before calling LLM
    output_admin = run_sql_pipeline(
        question="Tổng dư nợ ngắn hạn hiện tại?",
        role="quan_tri_he_thong",
        data_profile="real",
        llm_client=counting_client,
    )

    assert output_admin.status == "rejected"
    assert llm_calls == 0
    assert "not authorized" in (output_admin.error or "").lower()

    # 2. quan_ly_kho has only ai_v_ton_kho -> context strictly contains ONLY ai_v_ton_kho
    ctx_kho = build_sql_prompt_context(
        question="Tổng dư nợ ngắn hạn hiện tại?",
        role="quan_ly_kho",
        data_profile="real",
    )
    assert ctx_kho.allowed_views == {"ai_v_ton_kho"}
    assert "ai_v_ton_kho" in ctx_kho.catalog_markdown
    assert "ai_v_no_vay" not in ctx_kho.catalog_markdown
    assert "ai_v_bctc" not in ctx_kho.catalog_markdown
    assert "ai_v_dong_tien" not in ctx_kho.catalog_markdown


def test_sql_agent_attaches_synthetic_warning_on_synth_profile():
    """Review Focus #4: When data_profile == 'synth', attaches SYNTHETIC_DATA warning badge."""
    mock_client = MockSqlLLMClient(
        candidates=[
            SqlDraft(
                sql="SELECT SUM(principal_balance) FROM ai_views.ai_v_no_vay;",
                explanation_short="Tính tổng dư nợ trên synthetic profile",
                kpi_keys=["du_no_ngan_han"],
            )
        ]
    )

    app_synth = build_sql_graph(llm_client=mock_client)

    state_synth = app_synth.invoke({
        "request_id": "req-synth",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s-synth",
        "query": "Dư nợ ngắn hạn?",
        "data_profile": "synth",
    })

    assert "SYNTHETIC_DATA" in state_synth.get("warnings", [])

    state_real = app_synth.invoke({
        "request_id": "req-real",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s-real",
        "query": "Dư nợ ngắn hạn?",
        "data_profile": "real",
    })

    assert "SYNTHETIC_DATA" not in state_real.get("warnings", [])


def test_confidence_gate_preserves_clarification_flag():
    """Confidence gate preserves existing True or triggers True if status != ok or low confidence."""
    # Already True -> stays True
    res1 = confidence_gate_node({"needs_clarification": True, "sql": {"status": "ok", "confidence": 0.99}})
    assert res1["needs_clarification"] is True

    # Low confidence (< 0.45) -> sets True
    res2 = confidence_gate_node({"needs_clarification": False, "sql": {"status": "ok", "confidence": 0.30}}, min_confidence=0.45)
    assert res2["needs_clarification"] is True

    # High confidence & ok -> False
    res3 = confidence_gate_node({"needs_clarification": False, "sql": {"status": "ok", "confidence": 0.85}}, min_confidence=0.45)
    assert res3["needs_clarification"] is False

    # Status error -> True
    res4 = confidence_gate_node({"needs_clarification": False, "sql": {"status": "execution_error", "confidence": 0.0}})
    assert res4["needs_clarification"] is True
