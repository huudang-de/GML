"""LangGraph StateGraph orchestration pipeline."""

from collections.abc import Callable
import time
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.agents.intent import classify_intent_heuristic
from app.orchestration.routing import (
    route_after_confidence,
    route_after_intent,
    route_after_join,
)
from app.orchestration.state import ChatState, Intent


def _default_guard_input(state: ChatState) -> dict[str, Any]:
    return {}


def _default_resolve_context(state: ChatState) -> dict[str, Any]:
    query = state.get("query", "")
    return {"standalone_query": state.get("standalone_query", query)}


def _default_classify_intent(state: ChatState) -> dict[str, Any]:
    if state.get("intent"):
        return {"intent": state["intent"]}
    query = state.get("standalone_query") or state.get("query") or ""
    user = state.get("user") or {}
    role = user.get("role", "ceo")
    return {"intent": classify_intent_heuristic(query, role=role)}


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


def wrap_node_with_trace(
    node_name: str,
    fn: Callable[[ChatState], dict[str, Any]],
) -> Callable[[ChatState], dict[str, Any]]:
    """Wrap a node callable to measure execution latency and guarantee trace logging."""

    def traced_node(state: ChatState) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            res = fn(state) or {}
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            node_traces = res.get("trace")
            if isinstance(node_traces, list):
                found = False
                for tr in node_traces:
                    if isinstance(tr, dict):
                        # Normalize node name if internal agent used alternate label (e.g. advisor -> advise)
                        if tr.get("node") == "advisor" and node_name == "advise":
                            tr["node"] = "advise"
                        if tr.get("node") == node_name:
                            tr["latency_ms"] = round(elapsed_ms, 2)
                            found = True
                        elif "latency_ms" not in tr:
                            tr["latency_ms"] = round(elapsed_ms, 2)
                if not found:
                    node_traces.append({"node": node_name, "latency_ms": round(elapsed_ms, 2)})
            else:
                res["trace"] = [{"node": node_name, "latency_ms": round(elapsed_ms, 2)}]

            return res
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "errors": [f"{node_name} error: {e}"],
                "trace": [{"node": node_name, "latency_ms": round(elapsed_ms, 2), "status": "error"}],
            }

    return traced_node


def create_resolve_context_node(
    session_store: Any = None,
    text_llm_client: Any = None,
) -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph node that resolves multi-turn follow-up context."""
    from app.memory.followup import resolve_followup_query

    def resolve_context_node(state: ChatState) -> dict[str, Any]:
        session_id = state.get("session_id")
        user = state.get("user") or {}
        user_id = user.get("id", "default_user")
        data_profile = state.get("data_profile", "real")
        query = state.get("query", "")

        history = []
        if session_store and session_id:
            try:
                history = session_store.get_history(session_id=session_id, user_id=user_id, n=5)
            except Exception:
                history = []

        standalone_q, is_fu, cues = resolve_followup_query(
            query=query,
            history=history,
            data_profile=data_profile,
            llm_client=text_llm_client,
        )

        return {
            "standalone_query": standalone_q,
            "trace": [{
                "node": "resolve_context",
                "is_followup": is_fu,
                "cues": cues,
            }],
        }

    return resolve_context_node


def create_classify_intent_node(
    intent_llm_client: Any = None,
) -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph node that classifies intent using LLM or heuristic fallback."""
    from app.agents.intent import classify_intent

    def classify_intent_node(state: ChatState) -> dict[str, Any]:
        if state.get("intent"):
            return {
                "intent": state["intent"],
                "trace": [{"node": "classify_intent", "intent": state["intent"]}],
            }

        query = state.get("standalone_query") or state.get("query") or ""
        user = state.get("user") or {}
        role = user.get("role", "ceo")

        intent, errors = classify_intent(query=query, role=role, llm_client=intent_llm_client)
        update: dict[str, Any] = {
            "intent": intent,
            "trace": [{"node": "classify_intent", "intent": intent}],
        }
        if errors:
            update["errors"] = errors
        return update

    return classify_intent_node


def create_alert_summary_node(
    app_engine: Engine | None = None,
    settings: Any = None,
) -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph node that queries unacknowledged alerts from app.alert_event filtered by RBAC."""
    from app.core.security import get_allowed_views
    from app.knowledge.loader import get_kpi
    from db.apply_db import get_app_engine

    def alert_summary_node(state: ChatState) -> dict[str, Any]:
        engine = app_engine or get_app_engine(profile=state.get("data_profile", "real"))
        user = state.get("user") or {}
        role = user.get("role", "ceo")
        allowed_views = get_allowed_views(role)

        alerts: list[dict[str, Any]] = []
        try:
            stmt = sa.text("""
                SELECT id, rule_id, kpi_key, severity, message, value, threshold, created_at
                FROM app.alert_event
                WHERE is_acknowledged = FALSE
                ORDER BY created_at DESC;
            """)
            with engine.connect() as conn:
                rows = conn.execute(stmt).fetchall()

            for r in rows:
                try:
                    kpi_def = get_kpi(r.kpi_key)
                    if kpi_def.nguon_view not in allowed_views:
                        continue
                except Exception:
                    pass
                alerts.append({
                    "id": r.id,
                    "rule_id": r.rule_id,
                    "kpi_key": r.kpi_key,
                    "severity": r.severity,
                    "message": r.message,
                    "value": r.value,
                    "threshold": r.threshold,
                })
        except Exception as e:
            return {"alerts": [], "errors": [f"alert_summary error: {e}"], "trace": [{"node": "alert_summary", "alerts_count": 0}]}

        return {
            "alerts": alerts,
            "trace": [{"node": "alert_summary", "alerts_count": len(alerts)}],
        }

    return alert_summary_node


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


def build_v2_graph(
    sql_llm_client: Any = None,
    text_llm_client: Any = None,
    intent_llm_client: Any = None,
    rag_retriever: Any = None,
    session_store: Any = None,
    app_engine: Engine | None = None,
    settings: Any = None,
    node_overrides: dict[str, Callable[[ChatState], dict[str, Any]]] | None = None,
) -> CompiledStateGraph:
    """Build the production full-orchestrator LangGraph pipeline wiring all 14 nodes with latency tracing.

    Nodes:
    1. guard_input: blocks destructive DML/DDL, prompt injection, and RBAC violations
    2. resolve_context: resolves multi-turn follow-up and standalone queries
    3. classify_intent: routes to sql_only, rag_only, both, alert, or blocked
    4. sql_lookup: SQL generation, repair, and execution pipeline
    5. rag_lookup: hybrid semantic/keyword knowledge retrieval
    6. alert_summary: active threshold/anomaly alerts filtered by RBAC
    7. join: deterministic merge point for parallel branches
    8. explain: KPI narrative generation
    9. trend: historical time-series anomaly detection
    10. advise: CFO actionable recommendations
    11. confidence_gate: confidence routing threshold gate
    12. clarify: structured clarification requests for low confidence
    13. synthesize: composite typed response synthesis with numerical grounding
    14. guard_output: credential/internal schema sanitization and synthetic markers
    """
    from app.agents.advisor import create_advise_node
    from app.agents.explainer import create_explain_node
    from app.agents.rag_agent import create_rag_lookup_node
    from app.agents.sql_agent import confidence_gate_node, create_sql_lookup_node
    from app.agents.synthesizer import create_clarify_node, create_synthesize_node
    from app.agents.trend_agent import create_trend_node
    from app.orchestration.guards import create_guard_input_node, create_guard_output_node

    overrides = node_overrides or {}

    raw_nodes: dict[str, Callable[[ChatState], dict[str, Any]]] = {
        "guard_input": create_guard_input_node(),
        "resolve_context": create_resolve_context_node(session_store=session_store, text_llm_client=text_llm_client),
        "classify_intent": create_classify_intent_node(intent_llm_client=intent_llm_client),
        "sql_lookup": create_sql_lookup_node(llm_client=sql_llm_client, settings=settings),
        "rag_lookup": create_rag_lookup_node(retriever=rag_retriever, llm_client=text_llm_client),
        "alert_summary": create_alert_summary_node(app_engine=app_engine, settings=settings),
        "join": _default_join,
        "explain": create_explain_node(llm_client=text_llm_client),
        "trend": create_trend_node(),
        "advise": create_advise_node(llm_client=text_llm_client),
        "confidence_gate": confidence_gate_node,
        "clarify": create_clarify_node(settings=settings),
        "synthesize": create_synthesize_node(llm_client=text_llm_client, settings=settings),
        "guard_output": create_guard_output_node(),
    }

    traced_overrides: dict[str, Callable[[ChatState], dict[str, Any]]] = {}
    for name, raw_fn in raw_nodes.items():
        fn_to_use = overrides.get(name, raw_fn)
        traced_overrides[name] = wrap_node_with_trace(name, fn_to_use)

    return build_graph(node_overrides=traced_overrides)
