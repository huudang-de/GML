"""Chat router wiring the full LangGraph v2 orchestrator pipeline.

Specifications:
- Spec §5 T3, T4, T5
- POST /v1/chat endpoint contract
- Multi-turn conversation persistence in SessionStore
- Observability metric recording (node latency, SQL validity)
- Review Focus #3: Audit log sanitization (no financial result numbers in audit rows)
"""

import time
from typing import Any, Callable
import uuid

from fastapi import APIRouter, Depends, Request

from app.api.audit import extract_views_from_sql, write_audit_log
from app.api.deps import (
    check_rate_limit,
    get_current_user,
    get_metrics,
    get_request_id,
)
from app.api.schemas import ChatRequest, ChatResponse
from app.core.auth import UserPrincipal
from app.core.config import Settings, get_settings
from app.core.metrics import MetricsRegistry
from app.memory.session_store import SessionStore
from app.orchestration.graph import build_v2_graph
from app.orchestration.state import ChatState
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/chat", tags=["Chat"], dependencies=[Depends(check_rate_limit)])


def get_graph_builder() -> Callable[..., Any]:
    """Dependency provider for LangGraph orchestrator builder (allows test mocking/overrides)."""
    return build_v2_graph


@router.post("", response_model=ChatResponse)
def chat_turn(
    payload: ChatRequest,
    request: Request,
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    metrics: MetricsRegistry = Depends(get_metrics),
    graph_builder: Callable[..., Any] = Depends(get_graph_builder),
) -> ChatResponse:
    """Process a user conversational turn through the 14-node LangGraph pipeline."""
    t0 = time.perf_counter()
    req_id = get_request_id(request)

    # 1. Resolve data profile and session ID
    effective_profile = (payload.data_profile or settings.data_profile).strip().lower()
    session_id = payload.session_id.strip() if payload.session_id and payload.session_id.strip() else f"sess-{uuid.uuid4().hex[:12]}"

    # 2. Setup engines and session memory
    app_engine = get_app_engine(profile=effective_profile)
    session_store = SessionStore(
        engine=app_engine,
        data_profile=effective_profile,
        ttl_days=settings.session_ttl_days,
    )

    # 3. Build and execute LangGraph orchestrator pipeline
    graph = graph_builder(
        session_store=session_store,
        app_engine=app_engine,
        settings=settings,
    )

    initial_state: ChatState = {
        "request_id": req_id,
        "user": {"id": user.user_id, "role": user.role},
        "session_id": session_id,
        "query": payload.query,
        "data_profile": effective_profile,
    }

    final_state = graph.invoke(initial_state)
    execution_time_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    # 4. Extract answer and structured outputs
    answer_data = final_state.get("answer") or {}
    if not isinstance(answer_data, dict) and hasattr(answer_data, "model_dump"):
        answer_data = answer_data.model_dump()

    warnings_list = list(dict.fromkeys(
        list(final_state.get("warnings") or []) + list(answer_data.get("warnings") or [])
    ))

    # 5. Persist turn in SessionStore
    sql_block = final_state.get("sql") if isinstance(final_state.get("sql"), dict) else {}
    sql_executed = sql_block.get("sql")

    try:
        session_store.add_turn(
            session_id=session_id,
            user_id=user.user_id,
            query=payload.query,
            standalone_query=final_state.get("standalone_query"),
            intent=final_state.get("intent"),
            kpi_keys=final_state.get("kpi_keys"),
            sql_query=sql_executed,
            answer=answer_data,
            confidence=answer_data.get("confidence") if isinstance(answer_data, dict) else None,
            request_id=req_id,
        )
    except Exception:
        # Conversation state persistence failure should not abort response delivery
        pass

    # 6. Record node latencies and SQL validity into MetricsRegistry
    traces = final_state.get("trace") or []
    for tr in traces:
        if isinstance(tr, dict):
            node_name = tr.get("node")
            lat = tr.get("latency_ms")
            if node_name and lat is not None:
                try:
                    metrics.record_node_latency(str(node_name), float(lat))
                except Exception:
                    pass

    if sql_block and "status" in sql_block:
        metrics.record_sql_validity(sql_block.get("status") == "ok")

    # 7. Write audit log (Review Focus #3: NEVER store financial result numbers)
    views_accessed: list[str] = []
    if sql_executed:
        views_accessed = extract_views_from_sql(sql_executed)

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=payload.query,
        sql_executed=sql_executed,
        views_accessed=views_accessed,
        execution_time_ms=execution_time_ms,
    )

    return ChatResponse(
        session_id=session_id,
        answer=answer_data,
        warnings=warnings_list,
        request_id=req_id,
        standalone_query=final_state.get("standalone_query"),
        intent=final_state.get("intent"),
        data_profile=effective_profile,
        trace=traces,
    )
