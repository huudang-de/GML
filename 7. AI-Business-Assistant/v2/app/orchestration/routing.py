"""Routing logic for orchestrating LangGraph execution paths."""

from app.orchestration.state import ChatState


def route_after_intent(state: ChatState) -> list[str]:
    """Route to execution branch(es) based on classified intent.

    - sql_only: ['sql_lookup']
    - rag_only: ['rag_lookup']
    - both: ['sql_lookup', 'rag_lookup'] (parallel execution)
    - alert: ['alert_summary']
    - blocked: ['synthesize']
    - fallback: ['sql_lookup']
    """
    intent = state.get("intent")
    if intent == "sql_only":
        return ["sql_lookup"]
    if intent == "rag_only":
        return ["rag_lookup"]
    if intent == "both":
        return ["sql_lookup", "rag_lookup"]
    if intent == "alert":
        return ["alert_summary"]
    if intent == "blocked":
        return ["synthesize"]
    return ["sql_lookup"]


def route_after_join(state: ChatState) -> list[str]:
    """Route after joining parallel branches (sql, rag, alert).

    If kpi_keys are present, triggers parallel explanation and trend analysis.
    Otherwise skips directly to confidence gate.
    """
    if state.get("kpi_keys"):
        return ["explain", "trend"]
    return ["confidence_gate"]


def route_after_confidence(state: ChatState) -> str:
    """Route after confidence gate evaluation.

    If clarification is required, routes to clarify node.
    Otherwise routes to synthesize.
    """
    if state.get("needs_clarification"):
        return "clarify"
    return "synthesize"
