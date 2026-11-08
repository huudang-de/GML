"""KPI Calculation and Retrieval Router.

Specifications:
- TC-T5-02 & TC-T5-05: Zero-LLM deterministic KPI calculation via Golden Queries + RBAC enforcement.
- Review Focus #2: ScopedTTLCache strictly isolates (data_profile, role, kpi_key, as_of_date).
  RBAC checked BEFORE checking or setting cache.
- Spec §5 T5, §11.7
"""

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
from app.core.security import get_allowed_views
from app.knowledge.loader import get_kpi, load_golden_queries
from app.sql.executor import execute_validated_sql
from app.sql.validator import validate
from db.apply_db import get_app_engine, get_ro_engine

router = APIRouter(prefix="/v1/kpi", tags=["KPI"], dependencies=[Depends(check_rate_limit)])


@router.get("/{key}", response_model=KpiValueResponse)
def get_kpi_value(
    key: str,
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    cache: ScopedTTLCache = Depends(get_kpi_cache),
    metrics: MetricsRegistry = Depends(get_metrics),
) -> KpiValueResponse:
    """Retrieve and calculate KPI value using deterministic Golden Queries."""
    req_id = get_request_id(request)
    target_profile = (profile or settings.data_profile).strip().lower()

    # 1. Resolve KPI definition
    try:
        kpi_def = get_kpi(key)
    except KeyError:
        raise ApiException(
            status_code=404,
            code="KPI_NOT_FOUND",
            message=f"KPI '{key}' không tồn tại trong từ điển kiến thức kinh doanh.",
        )

    # 2. Review Focus #2: RBAC check BEFORE cache inspection or calculation
    allowed_views = get_allowed_views(user.role)
    required_views = set(kpi_def.nguon_view)

    if not required_views.issubset(allowed_views):
        app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=f"GET /v1/kpi/{key}",
            views_accessed=list(required_views),
        )
        raise ApiException(
            status_code=403,
            code="FORBIDDEN",
            message=(
                f"Vai trò '{user.role}' không có quyền truy cập KPI '{key}'. "
                f"Yêu cầu quyền trên view: {sorted(required_views)}."
            ),
        )

    # 3. Check ScopedTTLCache (isolated by profile, role, kpi_key, as_of_date)
    cache_key = cache.make_kpi_key(target_profile, user.role, key, str(settings.as_of_date))
    cached_payload = cache.get(cache_key)

    if cached_payload is not None:
        metrics.record_cache(hit=True)
        app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=f"GET /v1/kpi/{key}",
            sql_executed="[CACHE_HIT]",
            views_accessed=list(required_views),
        )
        res_data = dict(cached_payload)
        res_data["cached"] = True
        return KpiValueResponse(**res_data)

    metrics.record_cache(hit=False)

    # 4. Cache miss: Execute Golden Query without LLM invocation (TC-T5-02 & TC-T5-05)
    gqs = load_golden_queries()
    gq = next((q for q in gqs if q.id == kpi_def.golden_ref or q.kpi_key == key), None)
    if not gq or not gq.sql_text.strip():
        raise ApiException(
            status_code=500,
            code="GOLDEN_QUERY_MISSING",
            message=f"Không tìm thấy câu lệnh chuẩn Golden Query cho KPI '{key}' (ref: {kpi_def.golden_ref}).",
        )

    validated_sql = validate(gq.sql_text, allowed_tables=allowed_views)
    ro_engine = get_ro_engine(ro_uri=settings.get_ro_uri(profile=target_profile))
    exec_res = execute_validated_sql(validated_sql, profile=target_profile, engine=ro_engine)

    if exec_res.status != "ok" or not exec_res.rows:
        raise ApiException(
            status_code=500,
            code="KPI_EXECUTION_FAILED",
            message=f"Lỗi tính toán dữ liệu KPI '{key}': {exec_res.error or 'Không có kết quả trả về'}.",
        )

    if gq.value_column and gq.value_column in exec_res.rows[0]:
        val_raw = exec_res.rows[0][gq.value_column]
    else:
        val_raw = list(exec_res.rows[0].values())[0]

    val = float(val_raw) if val_raw is not None else 0.0

    warnings = ["SYNTHETIC_DATA"] if target_profile == "synth" else []

    payload = {
        "kpi_key": key,
        "kpi_name": kpi_def.ten,
        "value": val,
        "unit": kpi_def.don_vi,
        "as_of_date": str(settings.as_of_date),
        "data_profile": target_profile,
        "sql_executed": validated_sql,
        "warnings": warnings,
        "cached": False,
    }

    cache.set(cache_key, payload)

    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=f"GET /v1/kpi/{key}",
        sql_executed=validated_sql,
        views_accessed=list(required_views),
        execution_time_ms=exec_res.latency_ms,
    )

    return KpiValueResponse(**payload)
