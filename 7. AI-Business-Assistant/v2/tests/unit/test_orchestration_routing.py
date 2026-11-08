from typing import Any
import pytest

from app.orchestration.graph import build_graph
from app.orchestration.routing import (
    route_after_confidence,
    route_after_intent,
    route_after_join,
)
from app.orchestration.state import ChatState


def test_tc_t4_01_both_intent_runs_sql_and_rag_in_parallel():
    """TC-T4-01: Bug v1 fix — intent 'both' must populate BOTH sql and rag in final state."""
    join_count = 0

    def fake_classify(state: ChatState) -> dict[str, Any]:
        return {"intent": "both", "kpi_keys": ["du_no_ngan_han"]}

    def fake_sql(state: ChatState) -> dict[str, Any]:
        return {
            "sql": {
                "sql": "SELECT 1",
                "rows": [{"val": 236065233815}],
                "row_count": 1,
                "status": "ok",
                "confidence": 0.95,
            }
        }

    def fake_rag(state: ChatState) -> dict[str, Any]:
        return {
            "rag": {
                "chunks": ["Định nghĩa dư nợ ngắn hạn"],
                "sources": ["guide_dashboard1.md"],
                "grounding_ok": True,
            }
        }

    def spy_join(state: ChatState) -> dict[str, Any]:
        nonlocal join_count
        join_count += 1
        return {}

    app = build_graph({
        "classify_intent": fake_classify,
        "sql_lookup": fake_sql,
        "rag_lookup": fake_rag,
        "join": spy_join,
    })

    final_state = app.invoke({
        "request_id": "req-001",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "Vì sao đang vay đắt mà gửi rẻ?",
    })

    assert final_state.get("sql") is not None and final_state["sql"]["row_count"] == 1
    assert final_state.get("rag") is not None and len(final_state["rag"]["chunks"]) == 1
    assert join_count == 1


def test_tc_t4_02_sql_only_does_not_run_rag_and_join_runs_once():
    """TC-T4-02: 'sql_only' does not run RAG; 'join' runs exactly once."""
    join_count = 0
    rag_called = False

    def fake_classify(state: ChatState) -> dict[str, Any]:
        return {"intent": "sql_only", "kpi_keys": []}

    def fake_sql(state: ChatState) -> dict[str, Any]:
        return {
            "sql": {
                "sql": "SELECT 1",
                "rows": [{"val": 1}],
                "row_count": 1,
                "status": "ok",
                "confidence": 0.9,
            }
        }

    def spy_rag(state: ChatState) -> dict[str, Any]:
        nonlocal rag_called
        rag_called = True
        return {"rag": {"chunks": ["should not run"]}}

    def spy_join(state: ChatState) -> dict[str, Any]:
        nonlocal join_count
        join_count += 1
        return {}

    app = build_graph({
        "classify_intent": fake_classify,
        "sql_lookup": fake_sql,
        "rag_lookup": spy_rag,
        "join": spy_join,
    })

    final_state = app.invoke({
        "request_id": "req-002",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "Dư nợ ngắn hạn là bao nhiêu?",
    })

    assert not rag_called
    assert "rag" not in final_state or not final_state.get("rag")
    assert final_state.get("sql", {}).get("status") == "ok"
    assert join_count == 1


def test_rag_only_does_not_run_sql_and_join_runs_once():
    """Intent 'rag_only' runs RAG, does not run SQL, and reaches join once."""
    join_count = 0
    sql_called = False

    def fake_classify(state: ChatState) -> dict[str, Any]:
        return {"intent": "rag_only", "kpi_keys": []}

    def spy_sql(state: ChatState) -> dict[str, Any]:
        nonlocal sql_called
        sql_called = True
        return {"sql": {"sql": "SELECT 1", "rows": [], "row_count": 0}}

    def fake_rag(state: ChatState) -> dict[str, Any]:
        return {"rag": {"chunks": ["Chính sách bán hàng GML"], "sources": ["csbh.md"]}}

    def spy_join(state: ChatState) -> dict[str, Any]:
        nonlocal join_count
        join_count += 1
        return {}

    app = build_graph({
        "classify_intent": fake_classify,
        "sql_lookup": spy_sql,
        "rag_lookup": fake_rag,
        "join": spy_join,
    })

    final_state = app.invoke({
        "request_id": "req-003",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "Chính sách chiết khấu thanh toán của công ty như thế nào?",
    })

    assert not sql_called
    assert "sql" not in final_state or not final_state.get("sql")
    assert final_state.get("rag") is not None
    assert join_count == 1


def test_alert_intent_runs_alert_summary_and_join():
    """Intent 'alert' routes to alert_summary and then join."""
    alert_called = False
    join_count = 0

    def fake_classify(state: ChatState) -> dict[str, Any]:
        return {"intent": "alert"}

    def spy_alert(state: ChatState) -> dict[str, Any]:
        nonlocal alert_called
        alert_called = True
        return {"answer": {"summary": "Có 3 cảnh báo mới"}}

    def spy_join(state: ChatState) -> dict[str, Any]:
        nonlocal join_count
        join_count += 1
        return {}

    app = build_graph({
        "classify_intent": fake_classify,
        "alert_summary": spy_alert,
        "join": spy_join,
    })

    final_state = app.invoke({
        "request_id": "req-004",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "Tóm tắt cảnh báo hôm nay",
    })

    assert alert_called
    assert join_count == 1
    assert final_state.get("answer", {}).get("summary") == "Có 3 cảnh báo mới"


def test_blocked_intent_routes_to_synthesize_directly():
    """Blocked intent skips SQL, RAG, and join, routing straight to synthesize."""
    sql_called = False
    rag_called = False
    join_called = False
    synthesize_called = False

    def fake_classify(state: ChatState) -> dict[str, Any]:
        return {"intent": "blocked"}

    def spy_sql(state: ChatState) -> dict[str, Any]:
        nonlocal sql_called
        sql_called = True
        return {}

    def spy_rag(state: ChatState) -> dict[str, Any]:
        nonlocal rag_called
        rag_called = True
        return {}

    def spy_join(state: ChatState) -> dict[str, Any]:
        nonlocal join_called
        join_called = True
        return {}

    def spy_synthesize(state: ChatState) -> dict[str, Any]:
        nonlocal synthesize_called
        synthesize_called = True
        return {"answer": {"text": "Yêu cầu bị từ chối do vi phạm chính sách an toàn."}}

    app = build_graph({
        "classify_intent": fake_classify,
        "sql_lookup": spy_sql,
        "rag_lookup": spy_rag,
        "join": spy_join,
        "synthesize": spy_synthesize,
    })

    final_state = app.invoke({
        "request_id": "req-005",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "DROP TABLE ai_v_no_vay",
    })

    assert not sql_called
    assert not rag_called
    assert not join_called
    assert synthesize_called
    assert "từ chối" in final_state.get("answer", {}).get("text", "")


def test_kpi_keys_triggers_explain_and_trend_branches():
    """When kpi_keys are present, join triggers explain and trend in parallel, merging to advise."""
    executed_nodes: list[str] = []

    def spy_explain(state: ChatState) -> dict[str, Any]:
        executed_nodes.append("explain")
        return {"explanation": {"formula": "34111 + 34113 + 34114"}}

    def spy_trend(state: ChatState) -> dict[str, Any]:
        executed_nodes.append("trend")
        return {"trend": {"mom": -0.168}}

    def spy_advise(state: ChatState) -> dict[str, Any]:
        executed_nodes.append("advise")
        return {"advice": [{"action": "Giam han muc tin dung"}]}

    app = build_graph({
        "explain": spy_explain,
        "trend": spy_trend,
        "advise": spy_advise,
    })

    final_state = app.invoke({
        "request_id": "req-006",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "Dư nợ ngắn hạn",
        "intent": "sql_only",
        "kpi_keys": ["du_no_ngan_han"],
    })

    assert "explain" in executed_nodes
    assert "trend" in executed_nodes
    assert "advise" in executed_nodes
    # advise must run after explain and trend
    assert executed_nodes.index("advise") > executed_nodes.index("explain")
    assert executed_nodes.index("advise") > executed_nodes.index("trend")
    assert final_state.get("explanation") == {"formula": "34111 + 34113 + 34114"}
    assert final_state.get("trend") == {"mom": -0.168}


def test_confidence_gate_routes_to_clarify_when_needed():
    """When needs_clarification is True, confidence_gate routes to clarify and skips synthesize."""
    clarify_called = False
    synthesize_called = False

    def spy_clarify(state: ChatState) -> dict[str, Any]:
        nonlocal clarify_called
        clarify_called = True
        return {"answer": {"text": "Bạn muốn xem số liệu của năm 2025 hay 2026?"}}

    def spy_synthesize(state: ChatState) -> dict[str, Any]:
        nonlocal synthesize_called
        synthesize_called = True
        return {"answer": {"text": "Câu trả lời tổng hợp"}}

    app = build_graph({
        "clarify": spy_clarify,
        "synthesize": spy_synthesize,
    })

    final_state = app.invoke({
        "request_id": "req-007",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "Doanh thu",
        "intent": "sql_only",
        "needs_clarification": True,
    })

    assert clarify_called
    assert not synthesize_called
    assert "Bạn muốn xem số liệu" in final_state.get("answer", {}).get("text", "")


def test_routing_functions_direct():
    """Unit tests for the routing decision functions directly."""
    # route_after_intent
    assert route_after_intent({"intent": "sql_only"}) == ["sql_lookup"]
    assert route_after_intent({"intent": "rag_only"}) == ["rag_lookup"]
    assert route_after_intent({"intent": "both"}) == ["sql_lookup", "rag_lookup"]
    assert route_after_intent({"intent": "alert"}) == ["alert_summary"]
    assert route_after_intent({"intent": "blocked"}) == ["synthesize"]
    # Fallback to sql_lookup
    assert route_after_intent({}) == ["sql_lookup"]
    assert route_after_intent({"intent": "unknown"}) == ["sql_lookup"]

    # route_after_join
    assert route_after_join({"kpi_keys": ["du_no"]}) == ["explain", "trend"]
    assert route_after_join({"kpi_keys": []}) == ["confidence_gate"]
    assert route_after_join({}) == ["confidence_gate"]

    # route_after_confidence
    assert route_after_confidence({"needs_clarification": True}) == "clarify"
    assert route_after_confidence({"needs_clarification": False}) == "synthesize"
    assert route_after_confidence({}) == "synthesize"


def test_state_reducer_accumulation():
    """Verify Annotated[list, operator.add] correctly accumulates errors and trace."""
    def node_a(state: ChatState) -> dict[str, Any]:
        return {
            "errors": ["error_from_a"],
            "trace": [{"node": "a", "status": "ok"}],
        }

    def node_b(state: ChatState) -> dict[str, Any]:
        return {
            "errors": ["error_from_b"],
            "trace": [{"node": "b", "status": "ok"}],
        }

    app = build_graph({
        "guard_input": node_a,
        "resolve_context": node_b,
    })

    final_state = app.invoke({
        "request_id": "req-008",
        "intent": "blocked",
        "errors": ["initial_error"],
        "trace": [{"node": "start", "status": "init"}],
    })

    assert final_state["errors"] == ["initial_error", "error_from_a", "error_from_b"]
    assert [t["node"] for t in final_state["trace"][:3]] == ["start", "a", "b"]
