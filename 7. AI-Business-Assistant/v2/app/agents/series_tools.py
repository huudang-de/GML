"""Deterministic Series Tools & Alert Evidence Construction.

Specifications:
- Spec §5 T3 (TrendAnalyst & DecisionAdvisor Revision - P3r)
- M-08 Grounding: Zero DB/HTTP/LLM I/O; deterministic derivation only.
- TC-T3-15: Canonical series summarization and alert evidence grounding.
"""

from typing import Literal

from app.agents.models import AlertEvidence, SeriesSummary, Trend, TrendPoint
from app.knowledge.loader import get_business_actions, get_kpi

__all__ = [
    "AlertEvidence",
    "SeriesSummary",
    "build_alert_evidence",
    "summarize_series",
]


def summarize_series(series: list[TrendPoint], limit: int = 12) -> SeriesSummary:
    """Extract recent points and calculate trailing period-over-period delta.

    Args:
        series: Ordered list of historical TrendPoints.
        limit: Maximum number of trailing points to include (default 12).

    Returns:
        SeriesSummary containing sliced points, last value, previous value,
        and trailing delta percentage.
    """
    points = list(series[-limit:]) if limit > 0 else []
    last_value = points[-1].value if points else None
    previous_value = points[-2].value if len(points) >= 2 else None
    delta_pct = (
        (last_value - previous_value) / abs(previous_value)
        if previous_value is not None and previous_value != 0
        else None
    )
    return SeriesSummary(
        points=points,
        last_value=last_value,
        previous_value=previous_value,
        delta_pct=delta_pct,
    )


def build_alert_evidence(
    kpi_key: str,
    level: Literal["canh_bao", "nghiem_trong"] | str,
    value: float | None,
    trend: Trend | None,
    limit: int = 12,
) -> AlertEvidence:
    """Build deterministic grounding evidence package for KPI threshold alert.

    Args:
        kpi_key: Identifier of the KPI.
        level: Alert threshold level ('canh_bao' or 'nghiem_trong').
        value: Current scalar metric value trigger.
        trend: Trend analysis object containing historical series and anomalies.
        limit: Number of trailing time-series points to include (default 12).

    Returns:
        AlertEvidence populated with strictly grounded values and business rules.
    """
    try:
        kpi_def = get_kpi(kpi_key)
        threshold_expr = kpi_def.nguong.get(str(level))
    except KeyError:
        threshold_expr = None

    try:
        actions_info = get_business_actions(kpi_key, str(level))
        approved_actions = actions_info.get("actions", [])
        authority_role = actions_info.get("authority_role")
    except KeyError:
        approved_actions = []
        authority_role = None

    if trend is None:
        return AlertEvidence(
            kpi_key=kpi_key,
            level=level,  # type: ignore[arg-type]
            period=None,
            value=value,
            threshold_expr=threshold_expr,
            series=[],
            anomalies=[],
            coverage_warning="Không có dữ liệu chuỗi",
            approved_actions=approved_actions,
            authority_role=authority_role,
        )

    summary = summarize_series(trend.series, limit=limit)
    series_points = summary.points
    period_set = {p.period for p in series_points}
    anomalies = [a for a in trend.anomalies if a.period in period_set]
    period = series_points[-1].period if series_points else None
    coverage_warning = (
        f"Chỉ có {trend.data_coverage} tháng dữ liệu, chưa đủ để phân tích xu hướng"
        if trend.data_coverage < 6
        else None
    )

    return AlertEvidence(
        kpi_key=kpi_key,
        level=level,  # type: ignore[arg-type]
        period=period,
        value=value,
        threshold_expr=threshold_expr,
        series=series_points,
        anomalies=anomalies,
        coverage_warning=coverage_warning,
        approved_actions=approved_actions,
        authority_role=authority_role,
    )
