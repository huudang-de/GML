"""KPI Calculation and Retrieval Router.

Specifications:
- TC-T5-02 & TC-T5-05: Zero-LLM deterministic KPI calculation via Golden Queries + RBAC enforcement.
- Review Focus #2: ScopedTTLCache strictly isolates (data_profile, role, kpi_key, as_of_date).
  RBAC checked BEFORE checking or setting cache.
- Task 1 / P4r: Uses kpi_service layer and supports ?include=series query parameter.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from app.api.audit import write_audit_log
from app.api.deps import (
    ApiException,
    check_rate_limit,
    get_current_user,
    get_kpi_cache,
    get_metrics,
    get_request_id,
)
from app.api.schemas import KpiValueResponse
from app.core.auth import UserPrincipal
from app.core.cache import ScopedTTLCache
from app.core.config import Settings, get_settings
from app.core.metrics import MetricsRegistry
from app.services.kpi_service import (
    KpiComputationError,
    KpiForbidden,
    KpiNotFound,
    compute_kpi_series,
    compute_kpi_value,
)
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/kpi", tags=["KPI"], dependencies=[Depends(check_rate_limit)])


@router.get("/{key}", response_model=KpiValueResponse)
def get_kpi_value(
    key: str,
    request: Request,
    profile: str | None = Query(default=None),
    include: Literal["series"] | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    cache: ScopedTTLCache = Depends(get_kpi_cache),
    metrics: MetricsRegistry = Depends(get_metrics),
) -> KpiValueResponse:
    """Retrieve and calculate KPI value using deterministic Golden Queries, with optional time-series."""
    req_id = get_request_id(request)
    target_profile = (profile or settings.data_profile).strip().lower()

    # 1. Compute scalar KPI value
    try:
        payload, sql_executed, views, latency_ms, cached = compute_kpi_value(
            key=key,
            role=user.role,
            profile=target_profile,
            settings=settings,
            cache=cache,
        )
    except KpiNotFound as exc:
        app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=f"GET /v1/kpi/{key}",
            views_accessed=[],
        )
        raise ApiException(
            status_code=404,
            code="KPI_NOT_FOUND",
            message=str(exc),
        )
    except KpiForbidden as exc:
        app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=f"GET /v1/kpi/{key}",
            views_accessed=getattr(exc, "required_views", []),
        )
        raise ApiException(
            status_code=403,
            code="FORBIDDEN",
            message=str(exc),
        )
    except KpiComputationError as exc:
        app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=f"GET /v1/kpi/{key}",
            views_accessed=[],
        )
        raise ApiException(
            status_code=500,
            code="KPI_EXECUTION_FAILED",
            message=str(exc),
        )

    metrics.record_cache(hit=cached)

    # 2. Optionally load time-series
    summary = None
    if include == "series":
        try:
            summary = compute_kpi_series(
                key=key,
                role=user.role,
                profile=target_profile,
                settings=settings,
                cache=cache,
                limit=12,
            )
        except KpiForbidden as exc:
            app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
            write_audit_log(
                engine=app_engine,
                user_id=user.user_id,
                role=user.role,
                request_id=req_id,
                query=f"GET /v1/kpi/{key}",
                views_accessed=getattr(exc, "required_views", []),
            )
            raise ApiException(
                status_code=403,
                code="FORBIDDEN",
                message=str(exc),
            )
        except KpiComputationError as exc:
            app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
            write_audit_log(
                engine=app_engine,
                user_id=user.user_id,
                role=user.role,
                request_id=req_id,
                query=f"GET /v1/kpi/{key}",
                views_accessed=views,
            )
            raise ApiException(
                status_code=500,
                code="KPI_EXECUTION_FAILED",
                message=str(exc),
            )

    # 3. Exactly one audit log row per request
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=f"GET /v1/kpi/{key}",
        sql_executed=sql_executed,
        views_accessed=views,
        execution_time_ms=latency_ms,
    )

    # 4. Construct response
    res_data = dict(payload)
    res_data["cached"] = cached

    if include == "series" and summary is not None:
        res_data["series"] = [p.model_dump() for p in summary.points]
        res_data["previous_value"] = summary.previous_value
        res_data["delta_pct"] = summary.delta_pct
        if len(summary.points) < 6:
            res_data["series_warning"] = (
                f"Chỉ có {len(summary.points)} tháng dữ liệu, chưa đủ để phân tích xu hướng"
            )

    return KpiValueResponse(**res_data)
