"""Unit tests for Task 4: Synthesizer, Figure Provenance Verification, and Analytical Graph.

Specifications:
- TC-T3-13: Synthesizer typed Answer output & strict Figure provenance checking
- M-08 = 0%: Block hallucinated summary numbers, fall back to deterministic summary
- Review Focus #2: LangGraph node isolation without InvalidUpdateError in parallel branches
"""

from datetime import date
from typing import Any
import pytest

from app.agents.models import Answer, Figure
from app.agents.synthesizer import (
    create_clarify_node,
    create_synthesize_node,
    run_synthesizer,
    verify_figure_provenance,
)
from app.orchestration.graph import (
    build_analytical_graph,
    classify_intent_heuristic,
)
from app.orchestration.state import ChatState


class MockTextLLMClient:
    """Mock Text LLM Client returning fixed text or ungrounded numbers for testing."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.call_count = 0

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        self.call_count += 1
        return self.response_text


def test_tc_t3_13_synthesizer_typed_answer_and_figure_provenance():
    """TC-T3-13: Synthesizer outputs valid Answer.

    Every Figure.source_query_id MUST exist in execution logs.
    Fake query IDs (e.g. 'sql-fake999') are stripped and 'UNVERIFIED_FIGURE_STRIPPED'
    added to warnings.
    """
    valid_query_id = "sql-valid123"
    state: ChatState = {
        "request_id": "req-tc-t3-13",
        "data_profile": "real",
        "sql": {
            "sql": "SELECT du_no_ngan_han FROM ai_views.ai_v_no_vay",
            "columns": ["du_no_ngan_han"],
            "rows": [{"du_no_ngan_han": 236065233815.0}],
            "row_count": 1,
            "status": "ok",
            "confidence": 0.92,
            "source_query_id": valid_query_id,
        },
        "kpi_keys": ["du_no_ngan_han"],
        "warnings": [],
        "errors": [],
        "trace": [],
    }

    answer, warnings = run_synthesizer(state)

    # 1. Answer validates against Pydantic schema
    validated = Answer.model_validate(answer.model_dump())
    assert isinstance(validated, Answer)
    assert validated.request_id == "req-tc-t3-13"
    assert validated.confidence == 0.92
    assert len(validated.figures) >= 1

    # 2. All figures have valid source_query_id
    for fig in validated.figures:
        assert fig.source_query_id == valid_query_id

    # 3. Direct verification of verify_figure_provenance with fake query ID
    figures = [
        Figure(
            name="Dư nợ ngắn hạn hợp lệ",
            value=236065233815.0,
            unit="VNĐ",
            as_of=date(2026, 7, 31),
            source_query_id=valid_query_id,
        ),
        Figure(
            name="Dư nợ giả mạo",
            value=999999999999.0,
            unit="VNĐ",
            as_of=date(2026, 7, 31),
            source_query_id="sql-fake999",
        ),
    ]

    verified_figs, prov_warnings = verify_figure_provenance(
        figures=figures,
        valid_query_ids={valid_query_id},
    )

    assert len(verified_figs) == 1
    assert verified_figs[0].source_query_id == valid_query_id
    assert "UNVERIFIED_FIGURE_STRIPPED" in prov_warnings


def test_synthesizer_blocks_ungrounded_summary_numbers_m08_zero():
    """M-08 = 0%: Synthesizer blocks hallucinated numbers in LLM summary.

    When LLM hallucinates '999 tỷ VNĐ' while the true figure is ~236.07 tỷ VNĐ,
    Synthesizer tags 'UNGROUNDED_NUMBER' in warnings and replaces summary with
    deterministic summary that does not contain '999'.
    """
    hallucinating_client = MockTextLLMClient(
        "Theo số liệu mới nhất, dư nợ đạt 999 tỷ VNĐ và vượt hạn mức."
    )
    state: ChatState = {
        "request_id": "req-m08-gate",
        "data_profile": "real",
        "sql": {
            "sql": "SELECT du_no_ngan_han FROM ai_views.ai_v_no_vay",
            "columns": ["du_no_ngan_han"],
            "rows": [{"du_no_ngan_han": 236065233815.0}],
            "row_count": 1,
            "status": "ok",
            "confidence": 0.90,
            "source_query_id": "sql-m08-test",
        },
        "kpi_keys": ["du_no_ngan_han"],
        "warnings": [],
        "errors": [],
        "trace": [],
    }

    answer, warnings = run_synthesizer(state, llm_client=hallucinating_client)

    assert "UNGROUNDED_NUMBER" in answer.warnings
    assert "999" not in answer.summary
    assert "236" in answer.summary or "dư nợ" in answer.summary.lower()
    # Real data cutoff date check
    assert "31/07/2026" in answer.summary


def test_parallel_both_and_explain_trend_supersteps_no_invalid_update_error(tmp_path):
    """Review Focus #2: LangGraph node isolation in parallel execution.

    Runs build_analytical_graph with intent='both' on a question with
    kpi_keys=['ty_le_su_dung_han_muc'].
    Execution path:
      START -> guard_input -> resolve_context -> classify_intent
      -> [sql_lookup || rag_lookup] -> join
      -> [explain || trend] -> advise -> confidence_gate -> synthesize
      -> guard_output -> END.
    Must not raise InvalidUpdateError, and final state['answer'] must contain
    valid figures, sources, explanation, trend, and advice.
    """
    def mock_sql(state: ChatState) -> dict[str, Any]:
        return {
            "sql": {
                "sql": "SELECT 0.9182 AS ty_le_su_dung_han_muc",
                "columns": ["ty_le_su_dung_han_muc"],
                "rows": [{"ty_le_su_dung_han_muc": 0.9182}],
                "row_count": 1,
                "status": "ok",
                "confidence": 0.92,
                "source_query_id": "sql-mock-both",
                "latency_ms": 15.0,
            },
            "kpi_keys": ["ty_le_su_dung_han_muc"],
            "warnings": [],
            "trace": [{"node": "sql_lookup", "status": "ok"}],
        }

    def mock_rag(state: ChatState) -> dict[str, Any]:
        return {
            "rag": {
                "chunks": [{"source": "guide_dashboard1.md", "content": "Tỷ lệ sử dụng hạn mức vượt 90%"}],
                "sources": [
                    {
                        "citation_id": 1,
                        "source": "guide_dashboard1.md",
                        "heading_path": "Dashboard 1 > Thẻ KPI",
                        "snippet": "Tỷ lệ sử dụng hạn mức vượt 90%",
                        "score": 0.88,
                    }
                ],
                "answer_text": "Theo quy định Dashboard 1, khi tỷ lệ sử dụng hạn mức vượt 90% cần cảnh báo.",
                "grounding_ok": True,
                "latency_ms": 20.0,
            },
            "warnings": [],
            "trace": [{"node": "rag_lookup", "grounding_ok": True}],
        }

    graph = build_analytical_graph(
        node_overrides={
            "sql_lookup": mock_sql,
            "rag_lookup": mock_rag,
        }
    )

    initial_state: ChatState = {
        "request_id": "req-parallel-test",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "sess-parallel-01",
        "query": "Tỷ lệ sử dụng hạn mức hiện tại là bao nhiêu và vượt ngưỡng an toàn thì quy định xử lý thế nào?",
        "intent": "both",
        "data_profile": "real",
        "warnings": [],
        "errors": [],
        "trace": [],
    }

    final_state = graph.invoke(initial_state)

    # Assert no crash and full state propagation
    assert "answer" in final_state
    answer_dict = final_state["answer"]
    validated = Answer.model_validate(answer_dict)
    assert validated.request_id == "req-parallel-test"
    assert len(validated.figures) >= 1
    assert len(validated.sources) >= 1
    assert validated.explanation is not None
    assert validated.advice is not None


def test_classify_intent_heuristic_rules():
    """Test deterministic intent classification rules for Phase 3."""
    # 1. Blocked
    assert classify_intent_heuristic("INSERT INTO users VALUES ('x')") == "blocked"
    assert classify_intent_heuristic("xoá dữ liệu bảng fact_cashflow") == "blocked"

    # 2. Both (why / regulations along with numbers)
    assert classify_intent_heuristic("Vì sao đang vay đắt mà gửi rẻ?") == "both"
    assert classify_intent_heuristic("Hạn mức bao nhiêu và quy định xử lý thế nào?") == "both"

    # 3. RAG only (formula, definition, procedure)
    assert classify_intent_heuristic("Công thức tính hệ số LTV là gì?") == "rag_only"
    assert classify_intent_heuristic("Quy trình phê duyệt tín dụng ngân hàng?") == "rag_only"

    # 4. Default to sql_only
    assert classify_intent_heuristic("Dư nợ ngắn hạn hiện tại là bao nhiêu?") == "sql_only"
