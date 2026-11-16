"""TrendAnalyst Agent for 12-Month Time Series Analysis, MoM/MAD Anomaly Detection, and Seasonality.

Specifications:
- Spec Phần II §6 (Agent Architecture) & §5 T3 (TrendAnalyst)
- Zero LLM Calculation: Pure SQL on ai_views.* + deterministic rule-based algorithms
- Review Focus #3: MAD fallback when MAD == 0 and false-positive suppression on rebound month
- TC-T3-09 & M-09 (>= 90% anomaly recall) & M-10 (<= 1 false positive per KPI)
- TC-T3-10: Honest data coverage when data_coverage < 6 (no fabricated growth numbers)
"""

import re
import statistics
from typing import Any, Callable
import uuid

from sqlalchemy.engine import Engine

from app.agents.models import Trend, TrendAnomaly, TrendPoint
from app.core.security import get_allowed_views
from app.core.errors import SqlRejected
from app.knowledge.loader import (
    get_kpi,
    get_seasonality_insight,
    get_series_query,
    load_kpis,
)
from app.orchestration.state import ChatState
from app.sql.executor import execute_validated_sql
from app.sql.validator import validate
from db.apply_db import get_ro_engine


def check_threshold(value: float, expr: str) -> bool:
    """Evaluate a numeric value against a threshold expression string (e.g. '>= 0.70', '< 1.0')."""
    expr = expr.strip()
    try:
        if expr.startswith(">="):
            target = float(expr[2:].strip().replace(",", "."))
            return value >= target
        elif expr.startswith("<="):
            target = float(expr[2:].strip().replace(",", "."))
            return value <= target
        elif expr.startswith(">"):
            target = float(expr[1:].strip().replace(",", "."))
            return value > target
        elif expr.startswith("<"):
            target = float(expr[1:].strip().replace(",", "."))
            return value < target
        elif expr.startswith("=="):
            target = float(expr[2:].strip().replace(",", "."))
            return value == target
    except ValueError:
        return False
    return False


def detect_series_anomalies(
    kpi_key: str,
    series: list[TrendPoint],
    mom_threshold: float = 0.15,
    mad_k: float = 3.0,
    thresholds: dict[str, str] | None = None,
) -> list[TrendAnomaly]:
    """Detect anomalies in a numeric time series using Median Absolute Deviation (MAD),

    Month-over-Month (MoM) spikes, and static KPI thresholds.

    Review Focus #3:
    1. When MAD == 0 (e.g. 11/12 flat values and 1 spike), scale falls back to:
       scale = max(1.2533 * mean(|x - med|), 0.05 * max(abs(med), 1.0))
    2. Suppress false-positive MoM anomaly on the rebound month immediately following
       an isolated spike (|x_{t-1} - med| > mad_k * scale AND |x_t - med| <= 1.0 * scale).
    """
    if not series:
        return []

    values = [p.value for p in series]
    med = statistics.median(values)
    abs_devs = [abs(x - med) for x in values]
    mad = statistics.median(abs_devs)

    if mad > 0:
        scale = 1.4826 * mad
    else:
        mean_dev = statistics.mean(abs_devs)
        scale = max(1.2533 * mean_dev, 0.05 * max(abs(med), 1.0))

    anomalies: list[TrendAnomaly] = []
    th = thresholds or {}

    for t, pt in enumerate(series):
        x_t = pt.value
        mom_t: float | None = None
        if t > 0:
            prev_val = series[t - 1].value
            if prev_val != 0:
                mom_t = (x_t - prev_val) / abs(prev_val)
            else:
                mom_t = 0.0

        is_anomaly = False
        severity: str | None = None
        reason: str = ""

        # 1. Static threshold evaluation
        nt_expr = th.get("nghiem_trong")
        cb_expr = th.get("canh_bao")
        if nt_expr and check_threshold(x_t, nt_expr):
            is_anomaly = True
            severity = "nghiem_trong"
            reason = f"Vi phạm ngưỡng nghiêm trọng ({nt_expr})"
        elif cb_expr and check_threshold(x_t, cb_expr):
            is_anomaly = True
            severity = "canh_bao"
            reason = f"Vi phạm ngưỡng cảnh báo ({cb_expr})"

        # 2. Robust MAD Spike Detection
        abs_dev_cur = abs(x_t - med)
        if abs_dev_cur > mad_k * scale:
            is_anomaly = True
            mad_ratio = abs_dev_cur / scale if scale > 0 else 0.0
            if not severity:
                severity = "nghiem_trong" if abs_dev_cur >= 1.5 * mad_k * scale else "canh_bao"
                reason = f"Biến động vượt {mad_ratio:.1f} MAD so với trung vị ({med:,.2f})"

        # 3. MoM Spike Detection with Rebound Suppression
        # Rebound condition: previous month was an isolated spike, and current month returns to median
        is_rebound = False
        if t > 0:
            abs_dev_prev = abs(series[t - 1].value - med)
            if abs_dev_prev > mad_k * scale and abs_dev_cur <= 1.0 * scale:
                is_rebound = True

        if mom_t is not None and abs(mom_t) >= mom_threshold and not is_rebound:
            is_anomaly = True
            if not severity:
                severity = "nghiem_trong" if abs(mom_t) >= 0.50 else "canh_bao"
                direction = "tăng" if mom_t > 0 else "giảm"
                reason = f"Biến động MoM {direction} {mom_t:.1%}"

        if is_anomaly:
            anomalies.append(
                TrendAnomaly(
                    period=pt.period,
                    value=pt.value,
                    severity=severity or "canh_bao",
                    reason=reason,
                    mom_growth=mom_t,
                )
            )

    return anomalies


def _build_ton_kho_sku_sql(product_code: str | None = None) -> str:
    clean_code = (product_code or "SYNTH_SKU_MDF17").replace("'", "''")
    return f"""
    SELECT 
        to_char(tx_date, 'YYYY-MM') AS period,
        SUM(total_value) AS value
    FROM ai_views.ai_v_ton_kho
    WHERE record_type = 'balance'
      AND product_code = '{clean_code}'
    GROUP BY 1
    ORDER BY 1;
    """


# Intentional Phase 3 Exception:
# Keys 'ton_kho_sku' (parameterized by product_code), 'current_ratio', and
# 'doanh_thu_thuan' remain here in _NON_KPI_SERIES_SQL because they are either
# dynamically parameterized or used by eval/playbook without a static series_ref in T2.
_NON_KPI_SERIES_SQL: dict[str, Any] = {
    "ton_kho_sku": _build_ton_kho_sku_sql,
    "current_ratio": """
    SELECT 
        to_char(reporting_date, 'YYYY-MM') AS period,
        MAX(CASE WHEN item_code = 'B01-DN_100' THEN ending_balance END) /
        NULLIF(MAX(CASE WHEN item_code = 'B01-DN_310' THEN ending_balance END), 0) AS value
    FROM ai_views.ai_v_bctc
    WHERE report_type = 'B01-DN'
      AND item_code IN ('B01-DN_100', 'B01-DN_310')
    GROUP BY reporting_date
    ORDER BY reporting_date;
    """,
    "doanh_thu_thuan": """
    SELECT 
        to_char(reporting_date, 'YYYY-MM') AS period,
        SUM(ending_balance) AS value
    FROM ai_views.ai_v_bctc
    WHERE report_type = 'B02-DN'
      AND item_code = 'B02-DN_10'
    GROUP BY reporting_date
    ORDER BY reporting_date;
    """,
}


def _get_trend_sql(kpi_key: str, product_code: str | None = None) -> str:
    """Build time-series SQL for non-KPI keys remaining in Phase 3.

    Intentional Phase 3 Exception:
    Keys 'ton_kho_sku' (parameterized by product_code), 'current_ratio', and
    'doanh_thu_thuan' remain here in _NON_KPI_SERIES_SQL because they are either
    dynamically parameterized or used by eval/playbook without a static series_ref in T2.
    """
    if kpi_key in _NON_KPI_SERIES_SQL:
        entry = _NON_KPI_SERIES_SQL[kpi_key]
        if callable(entry):
            return entry(product_code)
        return entry
    raise KeyError(f"Unsupported KPI key for trend analysis: '{kpi_key}'")


def load_kpi_series(
    kpi_key: str,
    role: str = "ceo",
    data_profile: str = "real",
    engine: Engine | None = None,
    product_code: str | None = None,
) -> tuple[list[TrendPoint], str | None, str | None]:
    """Load canonical monthly time-series points for a KPI.

    Specifications:
    - Spec §5 T3 (TrendAnalyst Revision), TC-T3-14, TC-T3-15
    - Lookup order:
        1. T2 Knowledge layer: get_series_query(kpi_key)
        2. Non-KPI series fallback: _NON_KPI_SERIES_SQL (intentional Phase 3 exception)
        3. None: return ([], None, f"KPI '{kpi_key}' chưa có truy vấn chuỗi thời gian")
    - Role-based security validation via validate(raw_sql, allowed_tables)
    - SQL execution via execute_validated_sql
    - Returns sorted list of TrendPoint objects chronologically by period.

    Returns:
        tuple of (series_sorted, validated_sql, error)
    """
    raw_sql: str | None = None
    sq = get_series_query(kpi_key)
    if sq is not None and sq.sql_text:
        raw_sql = sq.sql_text
    elif kpi_key in _NON_KPI_SERIES_SQL:
        entry = _NON_KPI_SERIES_SQL[kpi_key]
        if callable(entry):
            raw_sql = entry(product_code)
        else:
            raw_sql = entry
    else:
        return [], None, f"KPI '{kpi_key}' chưa có truy vấn chuỗi thời gian"

    allowed_views = get_allowed_views(role)
    try:
        validated_sql = validate(raw_sql, allowed_tables=allowed_views)
    except SqlRejected as exc:
        return [], None, f"Quyền hạn của role '{role}' không đủ để xem dữ liệu cho KPI '{kpi_key}': {exc}"
    except Exception as exc:
        return [], None, f"SQL validation rejected: {exc}"

    active_engine = engine or get_ro_engine(profile=data_profile)
    exec_res = execute_validated_sql(validated_sql, engine=active_engine)
    if exec_res.error:
        return [], None, f"Lỗi truy vấn SQL: {exec_res.error}"

    series: list[TrendPoint] = []
    for row in exec_res.rows:
        p = str(row.get("period") or "")
        val = row.get("value")
        if p and val is not None:
            try:
                series.append(TrendPoint(period=p, value=float(val)))
            except (ValueError, TypeError):
                continue

    # Sort series chronologically
    series.sort(key=lambda x: x.period)
    return series, validated_sql, None


def analyze_kpi_trend(
    kpi_key: str,
    role: str = "ceo",
    data_profile: str = "real",
    engine: Engine | None = None,
    product_code: str | None = None,
) -> tuple[Trend | None, list[str], str | None]:
    """Execute pure SQL 12-month time series analysis for a KPI without LLM calls.

    Specifications:
    - Zero LLM calculation. Pure SQL on ai_views.* + deterministic algorithms.
    - Honest data coverage C1: when data_coverage < 6, mom_growth and yoy_growth
      are None, and warning 'Chỉ có {N} tháng dữ liệu, chưa đủ để phân tích xu hướng' is emitted.
    - Seasonality insight attached based on target closing month.
    """
    warnings: list[str] = []

    series, validated_sql, err = load_kpi_series(
        kpi_key=kpi_key,
        role=role,
        data_profile=data_profile,
        engine=engine,
        product_code=product_code,
    )
    if err:
        return None, warnings, err

    data_coverage = len(series)
    source_query_id = f"trend-{uuid.uuid4().hex[:8]}"

    # Load KPI metadata and thresholds
    thresholds: dict[str, str] = {}
    kpi_name = kpi_key
    kpis = load_kpis()
    if kpi_key in kpis:
        kpi_def = kpis[kpi_key]
        thresholds = kpi_def.nguong or {}
        kpi_name = kpi_def.ten
    elif kpi_key == "current_ratio":
        thresholds = {"canh_bao": "< 1.2", "nghiem_trong": "< 1.0"}
        kpi_name = "Hệ số khả năng thanh toán hiện thời (Current Ratio)"
    elif kpi_key == "ton_kho_sku":
        kpi_name = f"Giá trị tồn kho SKU ({product_code or 'MDF17'})"

    # Coverage logic (TC-T3-10)
    if data_coverage < 6:
        mom_growth = None
        yoy_growth = None
        warnings.append(f"Chỉ có {data_coverage} tháng dữ liệu, chưa đủ để phân tích xu hướng")
        anomalies: list[TrendAnomaly] = []
        # Check static thresholds only
        for pt in series:
            nt_expr = thresholds.get("nghiem_trong")
            cb_expr = thresholds.get("canh_bao")
            if nt_expr and check_threshold(pt.value, nt_expr):
                anomalies.append(
                    TrendAnomaly(
                        period=pt.period,
                        value=pt.value,
                        severity="nghiem_trong",
                        reason=f"Vi phạm ngưỡng nghiêm trọng ({nt_expr})",
                        mom_growth=None,
                    )
                )
            elif cb_expr and check_threshold(pt.value, cb_expr):
                anomalies.append(
                    TrendAnomaly(
                        period=pt.period,
                        value=pt.value,
                        severity="canh_bao",
                        reason=f"Vi phạm ngưỡng cảnh báo ({cb_expr})",
                        mom_growth=None,
                    )
                )
    else:
        # data_coverage >= 6
        if len(series) >= 2:
            prev = series[-2].value
            mom_growth = (series[-1].value - prev) / abs(prev) if prev != 0 else 0.0
        else:
            mom_growth = None

        if len(series) >= 13:
            prev_yr = series[-13].value
            yoy_growth = (series[-1].value - prev_yr) / abs(prev_yr) if prev_yr != 0 else 0.0
        else:
            yoy_growth = None

        anomalies = detect_series_anomalies(
            kpi_key=kpi_key,
            series=series,
            mom_threshold=0.15,
            mad_k=3.0,
            thresholds=thresholds,
        )

    # Seasonality insight attachment
    target_month = 7
    if series:
        period_parts = series[-1].period.split("-")
        if len(period_parts) >= 2 and period_parts[1].isdigit():
            target_month = int(period_parts[1])

    seasonality_insight = get_seasonality_insight(target_month)
    latest_period = series[-1].period if series else "chưa có"
    summary_text = (
        f"Phân tích xu hướng {kpi_name} ({kpi_key}) qua {data_coverage} kỳ dữ liệu (kỳ mới nhất: {latest_period}). "
        f"{seasonality_insight}"
    )
    if anomalies:
        summary_text += f" Phát hiện {len(anomalies)} kỳ có biến động bất thường."

    trend_obj = Trend(
        kpi_key=kpi_key,
        data_coverage=data_coverage,
        series=series,
        mom_growth=mom_growth,
        yoy_growth=yoy_growth,
        anomalies=anomalies,
        summary_text=summary_text,
        source_query_id=source_query_id,
    )

    return trend_obj, warnings, None


def create_trend_node() -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph node function for trend analysis.

    Review Focus #2: Node writes ONLY a subset of {'trend', 'warnings', 'trace', 'errors'}.
    """

    def trend_node(state: ChatState) -> dict[str, Any]:
        kpi_keys = state.get("kpi_keys", [])
        role = state.get("user", {}).get("role", "ceo")
        data_profile = state.get("data_profile", "real")
        product_code = state.get("product_code")

        primary_kpi = kpi_keys[0] if kpi_keys else None
        if not primary_kpi:
            return {
                "trend": {},
                "warnings": ["Không có KPI nào được chỉ định để phân tích xu hướng"],
                "trace": [{"node": "trend", "kpi_keys": [], "trend_present": False}],
            }

        trend_obj, warnings, error = analyze_kpi_trend(
            kpi_key=primary_kpi,
            role=role,
            data_profile=data_profile,
            product_code=product_code,
        )

        updates: dict[str, Any] = {
            "trend": trend_obj.model_dump() if trend_obj else {},
            "warnings": warnings,
            "trace": [
                {
                    "node": "trend",
                    "kpi_keys": kpi_keys,
                    "trend_present": trend_obj is not None,
                }
            ],
        }
        if error:
            updates["errors"] = [error]
        return updates

    return trend_node
