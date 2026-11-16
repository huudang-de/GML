"""KPI Service Layer for deterministic metric and time-series calculations.

Specifications:
- Brief: task-1-brief.md
- Plan: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 1)
- Review Focus #2: ScopedTTLCache strictly isolates (profile, role, key, as_of_date).
- RBAC enforcement strictly precedes cache inspection and calculation.
- compute_kpi_value: evaluates golden queries with deterministic zero-LLM execution.
- compute_kpi_series: loads time series points, computes trailing delta and sparkline points.
"""

from app.agents.models import SeriesSummary
from app.agents.series_tools import summarize_series
from app.agents.trend_agent import load_kpi_series
from app.core.cache import ScopedTTLCache
from app.core.config import Settings
from app.core.security import get_allowed_views
from app.knowledge.loader import get_kpi, load_golden_queries
from app.sql.executor import execute_validated_sql
from app.sql.validator import validate
from db.apply_db import get_ro_engine


class KpiForbidden(Exception):
    """Raised when the requesting role lacks access to the KPI's required views."""

    def __init__(self, message: str, required_views: list[str] | None = None) -> None:
        super().__init__(message)
        self.required_views = required_views or []


class KpiNotFound(Exception):
    """Raised when the requested KPI key does not exist in the knowledge catalog."""

    pass


class KpiComputationError(Exception):
    """Raised when SQL execution or deterministic KPI calculation fails."""

    pass


def compute_kpi_value(
    key: str,
    role: str,
    profile: str,
    settings: Settings,
    cache: ScopedTTLCache,
) -> tuple[dict, str | None, list[str], float | None, bool]:
    """Compute KPI scalar value using deterministic Golden Queries.

    Evaluation order:
    1. Knowledge lookup: verify KPI exists (KpiNotFound).
    2. RBAC check: verify role can access required views (KpiForbidden).
    3. ScopedTTLCache inspection: return cached payload if hit.
    4. Golden query execution: validate and run SQL on target profile engine.

    Returns:
        tuple of (payload, sql_executed, views_accessed, latency_ms, cached)
    """
    target_profile = (profile or settings.data_profile).strip().lower()
    as_of_str = str(settings.as_of_date)

    # 1. Resolve KPI definition
    try:
        kpi_def = get_kpi(key)
    except KeyError:
        raise KpiNotFound(f"KPI '{key}' không tồn tại trong từ điển kiến thức kinh doanh.")

    # 2. RBAC check BEFORE cache inspection or calculation
    allowed_views = get_allowed_views(role)
    required_views = set(kpi_def.nguon_view)

    if not required_views.issubset(allowed_views):
        raise KpiForbidden(
            f"Vai trò '{role}' không có quyền truy cập KPI '{key}'. "
            f"Yêu cầu quyền trên view: {sorted(required_views)}.",
            required_views=list(required_views),
        )

    # 3. Check ScopedTTLCache
    cache_key = cache.make_kpi_key(target_profile, role, key, as_of_str)
    cached_payload = cache.get(cache_key)

    if cached_payload is not None:
        res_data = dict(cached_payload)
        res_data["cached"] = True
        return res_data, "[CACHE_HIT]", list(required_views), None, True

    # 4. Cache miss: Execute Golden Query
    gqs = load_golden_queries()
    gq = next((q for q in gqs if q.id == kpi_def.golden_ref or q.kpi_key == key), None)
    if not gq or not gq.sql_text.strip():
        raise KpiComputationError(
            f"Không tìm thấy câu lệnh chuẩn Golden Query cho KPI '{key}' (ref: {kpi_def.golden_ref})."
        )

    try:
        validated_sql = validate(gq.sql_text, allowed_tables=allowed_views)
    except Exception as exc:
        raise KpiComputationError(f"SQL validation rejected: {exc}")

    ro_engine = get_ro_engine(ro_uri=settings.get_ro_uri(profile=target_profile))
    exec_res = execute_validated_sql(validated_sql, profile=target_profile, engine=ro_engine)

    if exec_res.status != "ok" or not exec_res.rows:
        raise KpiComputationError(
            f"Lỗi tính toán dữ liệu KPI '{key}': {exec_res.error or 'Không có kết quả trả về'}."
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
        "as_of_date": as_of_str,
        "data_profile": target_profile,
        "sql_executed": validated_sql,
        "warnings": warnings,
        "cached": False,
    }

    cache.set(cache_key, payload)
    return payload, validated_sql, list(required_views), exec_res.latency_ms, False


def compute_kpi_series(
    key: str,
    role: str,
    profile: str,
    settings: Settings,
    cache: ScopedTTLCache,
    limit: int = 12,
) -> SeriesSummary | None:
    """Compute KPI historical time-series and summary trailing metrics.

    Evaluation order:
    1. Knowledge lookup: verify KPI exists (KpiNotFound).
    2. RBAC check: verify role can access required views (KpiForbidden).
    3. ScopedTTLCache inspection: isolated via f"{key}#series" key format.
    4. Time-series query execution & summarization via summarize_series.

    Returns:
        SeriesSummary containing trailing points and delta_pct, or None if no series exists.
    """
    target_profile = (profile or settings.data_profile).strip().lower()
    as_of_str = str(settings.as_of_date)

    # 1. Resolve KPI definition
    try:
        kpi_def = get_kpi(key)
    except KeyError:
        raise KpiNotFound(f"KPI '{key}' không tồn tại trong từ điển kiến thức kinh doanh.")

    # 2. RBAC check BEFORE cache inspection or calculation
    allowed_views = get_allowed_views(role)
    required_views = set(kpi_def.nguon_view)

    if not required_views.issubset(allowed_views):
        raise KpiForbidden(
            f"Vai trò '{role}' không có quyền truy cập KPI '{key}'. "
            f"Yêu cầu quyền trên view: {sorted(required_views)}.",
            required_views=list(required_views),
        )

    # 3. Check ScopedTTLCache with series-specific key format (D9)
    series_cache_key = cache.make_kpi_key(target_profile, role, f"{key}#series", as_of_str)
    cached_summary = cache.get(series_cache_key)

    if cached_summary is not None:
        return cached_summary

    # 4. Cache miss: Load series points from canonical series queries
    ro_engine = get_ro_engine(ro_uri=settings.get_ro_uri(profile=target_profile))
    series_points, _validated_sql, err = load_kpi_series(
        kpi_key=key,
        role=role,
        data_profile=target_profile,
        engine=ro_engine,
    )

    if err:
        if "chưa có truy vấn chuỗi thời gian" in err:
            return None
        if "Lỗi truy vấn SQL" in err:
            raise KpiComputationError(err)
        return None

    if not series_points:
        return None

    summary = summarize_series(series_points, limit=limit)
    cache.set(series_cache_key, summary)
    return summary
