"""Session conversation history management router strictly scoped to authenticated user.

Specifications:
- TC-T2-07 & Review Focus #1: Zero cross-user memory leakage on retrieval or deletion.
- Spec §5 T5, §11.7
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request

from app.api.audit import write_audit_log
from app.api.deps import (
    check_rate_limit,
    get_current_user,
    get_request_id,
)
from app.api.schemas import (
    HistoryDeleteResponse,
    HistoryListResponse,
    HistoryTurnItem,
)
from app.core.auth import UserPrincipal
from app.core.config import Settings, get_settings
from app.memory.session_store import SessionStore
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/history", tags=["History"], dependencies=[Depends(check_rate_limit)])


@router.get("", response_model=HistoryListResponse)
def get_user_history(
    request: Request,
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> HistoryListResponse:
    """Retrieve conversation history strictly isolated by caller's user_id."""
    req_id = get_request_id(request)
    target_profile = (profile or settings.data_profile).strip().lower()
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
    store = SessionStore(engine=app_engine, data_profile=target_profile, ttl_days=settings.session_ttl_days)
    records = store.list_user_turns(user_id=user.user_id, session_id=session_id, limit=limit)

    items: list[HistoryTurnItem] = []
    for r in records:
        summary = None
        if isinstance(r.answer, dict):
            summary = r.answer.get("summary")
        created_str = r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at)

        items.append(
            HistoryTurnItem(
                turn_id=r.id,
                session_id=r.session_id,
                query=r.query,
                answer_summary=summary,
                intent=r.intent,
                created_at=created_str,
            )
        )

    app_engine = get_app_engine(profile=target_profile)
    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=f"GET /v1/history (session_id={session_id}, limit={limit})",
    )

    return HistoryListResponse(turns=items, total=len(items))


@router.delete("", response_model=HistoryDeleteResponse)
def delete_user_history(
    request: Request,
    session_id: str | None = Query(default=None),
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> HistoryDeleteResponse:
    """Delete conversation history strictly scoped to caller's user_id."""
    req_id = get_request_id(request)
    target_profile = (profile or settings.data_profile).strip().lower()
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
    store = SessionStore(engine=app_engine, data_profile=target_profile, ttl_days=settings.session_ttl_days)
    deleted_cnt = store.delete_user_history(user_id=user.user_id, session_id=session_id)

    app_engine = get_app_engine(profile=target_profile)
    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=f"DELETE /v1/history (session_id={session_id})",
    )

    return HistoryDeleteResponse(deleted_count=deleted_cnt, status="ok")
