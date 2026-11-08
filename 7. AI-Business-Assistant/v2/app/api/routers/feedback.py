"""Feedback collection router for chat responses.

Specifications:
- Spec §5 T5, §11.7
"""

from fastapi import APIRouter, Depends, Query, Request
import sqlalchemy as sa

from app.api.audit import write_audit_log
from app.api.deps import (
    ApiException,
    check_rate_limit,
    get_current_user,
    get_request_id,
)
from app.api.schemas import FeedbackRequest, FeedbackResponse
from app.core.auth import UserPrincipal
from app.core.config import Settings, get_settings
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/feedback", tags=["Feedback"], dependencies=[Depends(check_rate_limit)])


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    body: FeedbackRequest,
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> FeedbackResponse:
    """Submit qualitative feedback (rating: up/down) for a query turn."""
    req_id = get_request_id(request)
    target_profile = (profile or settings.data_profile).strip().lower()
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))

    stmt = sa.text("""
        INSERT INTO app.feedback (request_id, user_id, rating, note, created_at)
        VALUES (:request_id, :user_id, :rating, :note, now())
        RETURNING id;
    """)

    with app_engine.begin() as conn:
        feed_id = conn.execute(
            stmt,
            {
                "request_id": body.request_id,
                "user_id": user.user_id,
                "rating": body.rating,
                "note": body.comment,
            },
        ).scalar()

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=f"POST /v1/feedback (rating={body.rating}, target_request_id={body.request_id})",
    )

    return FeedbackResponse(
        id=int(feed_id) if feed_id is not None else None,
        status="ok",
        message="Feedback recorded",
    )
