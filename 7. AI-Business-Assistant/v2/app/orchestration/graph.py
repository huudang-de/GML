"""LangGraph StateGraph orchestration pipeline."""

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.orchestration.routing import (
    route_after_confidence,
    route_after_intent,
    route_after_join,
)
from app.orchestration.state import ChatState, Intent


def classify_intent_heuristic(query: str) -> Intent:
    """Classify user query intent into sql_only, rag_only, both, or blocked based on deterministic rules."""
    q = query.lower().strip()

    # 1. Blocked intent check (DML / DDL / sensitive operations)
    blocked_keywords = [
        "insert into", "delete from", "drop table", "alter table", "update ",
        "thêm dữ liệu", "xoá dữ liệu", "xóa dữ liệu", "sửa dữ liệu", "cập nhật dữ liệu",
        "thay đổi mật khẩu", "reset password", "truncate ",
    ]
    if any(kw in q for kw in blocked_keywords):
        return "blocked"

    # 2. Both intent check (asking why, regulations on how to handle, strategy along with numbers/kpi)
    both_keywords = [
        "tại sao", "tai sao", "vì sao", "vi sao",
        "quy định xử lý", "quy dinh xu ly",
        "chiến lược", "chien luoc",
        "lý do", "ly do", "nguyên nhân", "nguyen nhan",
        "kịch bản ứng phó", "kich ban ung pho",
    ]
    if any(kw in q for kw in both_keywords):
        return "both"

    # 3. RAG only intent check (formula, definition, how to calculate, procedure, policy)
    rag_keywords = [
        "công thức", "cong thuc", "định nghĩa", "dinh nghia",
        "tính thế nào", "tinh the nao", "cách tính", "cach tinh",
        "quy trình", "quy trinh", "chính sách", "chinh sach",
        "hướng dẫn", "huong dan", "tài liệu", "tai lieu",
        "cẩm nang", "cam nang", "story telling",
    ]
    if any(kw in q for kw in rag_keywords):
        return "rag_only"

    # 4. Default to sql_only
    return "sql_only"


def _default_guard_input(state: ChatState) -> dict[str, Any]:
    return {}


def _default_resolve_context(state: ChatState) -> dict[str, Any]:
    query = state.get("query", "")
    return {"standalone_query": state.get("standalone_query", query)}


def _default_classify_intent(state: ChatState) -> dict[str, Any]:
    if state.get("intent"):
        return {"intent": state["intent"]}
    query = state.get("standalone_query") or state.get("query") or ""
    return {"intent": classify_intent_heuristic(query)}


def _default_sql_lookup(state: ChatState) -> dict[str, Any]:
    return {}


def _default_rag_lookup(state: ChatState) -> dict[str, Any]:
    return {}


def _default_alert_summary(state: ChatState) -> dict[str, Any]:
    return {}


def _default_join(state: ChatState) -> dict[str, Any]:
    """Node gom nhánh song song (Review Focus #5).

    Returns an empty update so LangGraph synchronizes all incoming parallel
    branches while fully preserving existing state (e.g. sql, rag).
    """
    return {}


def _default_explain(state: ChatState) -> dict[str, Any]:
    return {}


def _default_trend(state: ChatState) -> dict[str, Any]:
    return {}


def _default_advise(state: ChatState) -> dict[str, Any]:
    return {}


def _default_confidence_gate(state: ChatState) -> dict[str, Any]:
    return {}


def _default_clarify(state: ChatState) -> dict[str, Any]:
    return {}


def _default_synthesize(state: ChatState) -> dict[str, Any]:
    return {}


def _default_guard_output(state: ChatState) -> dict[str, Any]:
    return {}


DEFAULT_NODES: dict[str, Callable[[ChatState], dict[str, Any]]] = {
    "guard_input": _default_guard_input,
    "resolve_context": _default_resolve_context,
    "classify_intent": _default_classify_intent,
    "sql_lookup": _default_sql_lookup,
    "rag_lookup": _default_rag_lookup,
    "alert_summary": _default_alert_summary,
    "join": _default_join,
    "explain": _default_explain,
    "trend": _default_trend,
    "advise": _default_advise,
    "confidence_gate": _default_confidence_gate,
    "clarify": _default_clarify,
    "synthesize": _default_synthesize,
    "guard_output": _default_guard_output,
}


def build_graph(
    node_overrides: dict[str, Callable[[ChatState], dict[str, Any]]] | None = None,
) -> CompiledStateGraph:
    """Build and compile the LangGraph StateGraph orchestrator.

    Args:
        node_overrides: Optional mapping of node names to custom callable
          implementations (useful for unit/integration testing individual nodes
          or mocking LLM/DB agent responses).

    Returns:
        CompiledStateGraph runnable.
    """
    overrides = node_overrides or {}
    graph = StateGraph(ChatState)

    # Register nodes
    for name, default_fn in DEFAULT_NODES.items():
        fn = overrides.get(name, default_fn)
        graph.add_node(name, fn)

    # Entry sequence: START -> guard_input -> resolve_context -> classify_intent
    graph.add_edge(START, "guard_input")
    graph.add_edge("guard_input", "resolve_context")
    graph.add_edge("resolve_context", "classify_intent")

    # Intent routing (may branch to parallel [sql_lookup, rag_lookup], or alert, or synthesize)
    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        ["sql_lookup", "rag_lookup", "alert_summary", "synthesize"],
    )

    # Parallel merge into join node
    graph.add_edge("sql_lookup", "join")
    graph.add_edge("rag_lookup", "join")
    graph.add_edge("alert_summary", "join")

    # Routing after join (parallel explain & trend if KPI keys, else direct to confidence gate)
    graph.add_conditional_edges(
        "join",
        route_after_join,
        ["explain", "trend", "confidence_gate"],
    )

    # explain and trend both merge into advise
    graph.add_edge("explain", "advise")
    graph.add_edge("trend", "advise")
    graph.add_edge("advise", "confidence_gate")

    # Confidence gate routing: clarify or synthesize
    graph.add_conditional_edges(
        "confidence_gate",
        route_after_confidence,
        ["clarify", "synthesize"],
    )

    # Exit sequence: clarify/synthesize -> guard_output -> END
    graph.add_edge("clarify", "guard_output")
    graph.add_edge("synthesize", "guard_output")
    graph.add_edge("guard_output", END)

    return graph.compile()


def build_sql_graph(
    llm_client: Any = None,
    settings: Any = None,
    node_overrides: dict[str, Callable[[ChatState], dict[str, Any]]] | None = None,
) -> CompiledStateGraph:
    """Build LangGraph state graph wiring real/mock SQLAgent node and confidence gate node.

    Args:
        llm_client: Optional SqlLLMClient instance.
        settings: Optional Settings instance.
        node_overrides: Optional node overrides.
    """
    from app.agents.sql_agent import confidence_gate_node, create_sql_lookup_node

    overrides: dict[str, Callable[[ChatState], dict[str, Any]]] = {
        "sql_lookup": create_sql_lookup_node(llm_client=llm_client, settings=settings),
        "confidence_gate": confidence_gate_node,
    }
    if node_overrides:
        overrides.update(node_overrides)

    return build_graph(node_overrides=overrides)


def build_analytical_graph(
    sql_llm_client: Any = None,
    text_llm_client: Any = None,
    rag_retriever: Any = None,
    settings: Any = None,
    node_overrides: dict[str, Callable[[ChatState], dict[str, Any]]] | None = None,
) -> CompiledStateGraph:
    """Build LangGraph StateGraph wiring all T2-RAG and T3 analytical agents into a composite pipeline.

    Wired Agents:
    - classify_intent: intent routing using classify_intent_heuristic
    - sql_lookup: SQLAgent pipeline node
    - rag_lookup: RAGAgent semantic retrieval node
    - explain: ExplainerAgent KPI narrative node
    - trend: TrendAnalystAgent time-series anomaly node
    - advise: DecisionAdvisorAgent recommendation node
    - confidence_gate: confidence validation node
    - clarify: clarification node for low confidence / missing data
    - synthesize: SynthesizerAgent composite typed Answer node

    Preserves existing build_graph() and build_sql_graph() without regressions.
    """
    from app.agents.advisor import create_advise_node
    from app.agents.explainer import create_explain_node
    from app.agents.rag_agent import create_rag_lookup_node
    from app.agents.sql_agent import confidence_gate_node, create_sql_lookup_node
    from app.agents.synthesizer import create_clarify_node, create_synthesize_node
    from app.agents.trend_agent import create_trend_node

    overrides: dict[str, Callable[[ChatState], dict[str, Any]]] = {
        "sql_lookup": create_sql_lookup_node(llm_client=sql_llm_client, settings=settings),
        "rag_lookup": create_rag_lookup_node(retriever=rag_retriever, llm_client=text_llm_client),
        "explain": create_explain_node(llm_client=text_llm_client),
        "trend": create_trend_node(),
        "advise": create_advise_node(llm_client=text_llm_client),
        "confidence_gate": confidence_gate_node,
        "clarify": create_clarify_node(settings=settings),
        "synthesize": create_synthesize_node(llm_client=text_llm_client, settings=settings),
    }
    if node_overrides:
        overrides.update(node_overrides)

    return build_graph(node_overrides=overrides)
