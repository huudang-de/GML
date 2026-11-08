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
from app.orchestration.state import ChatState


def _default_guard_input(state: ChatState) -> dict[str, Any]:
    return {}


def _default_resolve_context(state: ChatState) -> dict[str, Any]:
    query = state.get("query", "")
    return {"standalone_query": state.get("standalone_query", query)}


def _default_classify_intent(state: ChatState) -> dict[str, Any]:
    return {"intent": state.get("intent", "sql_only")}


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
