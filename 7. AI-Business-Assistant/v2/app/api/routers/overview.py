"""Overview briefing router with role-based aggregation, caching, and audit trail.

Specifications:
- Spec: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 5)
- Endpoint: GET /v1/overview
- Produces: OverviewResponse
- Audit trail: Exactly 1 row in app.audit_log with query="GET /v1/overview" and union of KPI views.
"""

import time
from fastapi import APIRouter, Depends, Query, Request

from app.api.audit import write_audit_log
from app.api.deps import (
    check_rate_limit,
    get_current_user,
    get_kpi_cache,
    get_request_id,
    resolve_profile,
)
from app.api.schemas import OverviewResponse
from app.core.auth import UserPrincipal
from app.core.cache import ScopedTTLCache
from app.core.config import Settings, get_settings
from app.knowledge.loader import get_kpi
from app.services.briefing import build_briefing
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/overview", tags=["Overview"], dependencies=[Depends(check_rate_limit)])


@router.get("", response_model=OverviewResponse)
def get_overview(
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    cache: ScopedTTLCache = Depends(get_kpi_cache),
) -> OverviewResponse:
    """Retrieve executive overview tailored for the authenticated user's role and data profile."""
    req_id = get_request_id(request)
    target_profile = resolve_profile(profile, settings, user=user)
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))

    start_time = time.perf_counter()
    response = build_briefing(
        user=user,
        profile=target_profile,
        settings=settings,
        cache=cache,
        app_engine=app_engine,
    )
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    # Collect union of views from rendered KPI cards
    views_accessed: set[str] = set()
    for card in response.kpis:
        try:
            kpi_def = get_kpi(card.kpi_key)
            views_accessed.update(kpi_def.nguon_view)
        except KeyError:
            pass

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query="GET /v1/overview",
        views_accessed=sorted(list(views_accessed)),
        execution_time_ms=latency_ms,
    )

    return response
