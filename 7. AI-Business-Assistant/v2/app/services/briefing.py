"""Briefing Service for constructing role-based executive overviews.

Specifications:
- Spec: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 5)
- Brief: task-5-brief.md
- Consumes: get_role_profile, compute_kpi_value, compute_kpi_series,
            app.alert_event, app.action_item, app.pinned_kpi, app.job_heartbeat.
- Produces: OverviewResponse
"""

from datetime import datetime
import json
from typing import Any
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.api.schemas import AlertItem, OverviewKpiCard, OverviewResponse
from app.core.auth import UserPrincipal
from app.core.cache import ScopedTTLCache
from app.core.config import Settings
from app.core.security import can_access_kpi, kpi_domain
from app.knowledge.loader import get_kpi, get_role_profile
from app.services.kpi_service import (
    KpiComputationError,
    KpiForbidden,
    KpiNotFound,
    compute_kpi_series,
    compute_kpi_value,
    series_warning_for_summary,
)


def row_to_alert_item(r: Any) -> AlertItem:
    """Convert an app.alert_event row into an AlertItem schema object safely."""
    try:
        row_domain = kpi_domain(r.kpi_key)
    except (KeyError, ValueError):
        row_domain = None

    created_str = r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at)
    ack_str = (
        r.acknowledged_at.isoformat()
        if isinstance(r.acknowledged_at, datetime)
        else (str(r.acknowledged_at) if r.acknowledged_at else None)
    )
    esc_str = (
        r.escalated_at.isoformat()
        if isinstance(r.escalated_at, datetime)
        else (str(r.escalated_at) if r.escalated_at else None)
    )

    raw_ev = r.evidence
    ev_dict: dict[str, Any] | None = None
    if isinstance(raw_ev, str):
        try:
            parsed = json.loads(raw_ev)
            if isinstance(parsed, dict):
                ev_dict = parsed
        except Exception:
            ev_dict = None
    elif isinstance(raw_ev, dict):
        ev_dict = raw_ev

    return AlertItem(
        id=r.id,
        rule_id=r.rule_id,
        kpi_key=r.kpi_key,
        severity=r.severity,
        alert_level=r.severity,
        message=r.message,
        current_value=r.value,
        threshold_value=r.threshold,
        value=r.value,
        threshold=r.threshold,
        is_acknowledged=bool(r.is_acknowledged),
        created_at=created_str,
        acknowledged_at=ack_str,
        acknowledged_by=r.acknowledged_by,
        period=r.period,
        evidence=ev_dict,
        domain=row_domain,
        escalated_at=esc_str,
        occurrence_count=int(getattr(r, "occurrence_count", 1) or 1),
    )


def build_briefing(
    user: UserPrincipal,
    profile: str,
    settings: Settings,
    cache: ScopedTTLCache,
    app_engine: Engine,
) -> OverviewResponse:
    """Build the operational briefing / overview tailored for the user's role and data profile.

    Step breakdown:
    1. Resolve role profile (overview KPIs and suggested questions).
    2. Query pinned KPIs for (user_id, data_profile).
    3. Compose ordered KPI list: overview_kpis + un-duplicated pinned keys; filter by RBAC.
    4. Compute KPI cards individually:
       - Each card is isolated in try/except; KpiComputationError sets card.error without failing response (TC-T5-12).
       - Series summary attached if available; degrades gracefully if missing.
    5. Query unacknowledged alerts:
       - RBAC filtered; safely parses evidence and maps domains.
       - Aggregates open alert counts by severity.
       - Takes top 3 most severe alerts for display.
    6. Count active action items visible to caller.
    7. Retrieve timestamp of latest successful alert engine run from job heartbeat.
    """
    target_profile = (profile or settings.data_profile).strip().lower()
    as_of_str = str(settings.as_of_date)

    # 1. Resolve role profile
    role_profile = get_role_profile(user.role)
    greeting_title = role_profile.greeting_title or user.role

    # 2. Query pinned KPIs
    pinned_stmt = sa.text("""
        SELECT kpi_key
        FROM app.pinned_kpi
        WHERE user_id = :uid AND data_profile = :profile
        ORDER BY position ASC, id ASC;
    """)
    with app_engine.connect() as conn:
        pinned_rows = conn.execute(pinned_stmt, {"uid": user.user_id, "profile": target_profile}).fetchall()

    pinned_keys = [r.kpi_key for r in pinned_rows]
    pinned_set = set(pinned_keys)

    # 3. Compose ordered KPI candidate keys
    candidate_keys: list[str] = []
    for k in role_profile.overview_kpis:
        if k not in candidate_keys:
            candidate_keys.append(k)
    for k in pinned_keys:
        if k not in candidate_keys:
            candidate_keys.append(k)

    # Filter candidates by KPI catalog existence and RBAC
    ordered_kpi_keys: list[str] = []
    for k in candidate_keys:
        try:
            get_kpi(k)
        except KeyError:
            continue
        if not can_access_kpi(user.role, k):
            continue
        ordered_kpi_keys.append(k)

    # 4. Compute KPI cards individually
    cards: list[OverviewKpiCard] = []
    for kpi_key in ordered_kpi_keys:
        is_pinned = kpi_key in pinned_set
        try:
            kpi_def = get_kpi(kpi_key)
            kpi_name = kpi_def.ten
            unit = kpi_def.don_vi
        except KeyError:
            kpi_name = None
            unit = None

        try:
            domain = kpi_domain(kpi_key)
        except (KeyError, ValueError):
            domain = "khac"

        val: float | None = None
        prev_val: float | None = None
        delta_pct: float | None = None
        series_points: list[dict[str, Any]] = []
        card_error: str | None = None
        series_warn: str | None = None

        try:
            val_payload, _sql, _views, _lat, _cached = compute_kpi_value(
                key=kpi_key,
                role=user.role,
                profile=target_profile,
                settings=settings,
                cache=cache,
            )
            val = val_payload.get("value")
            if val_payload.get("kpi_name"):
                kpi_name = val_payload["kpi_name"]
            if val_payload.get("unit"):
                unit = val_payload["unit"]
        except (KpiComputationError, KpiForbidden, KpiNotFound, sa.exc.SQLAlchemyError) as exc:
            card_error = str(exc)

        if card_error is None:
            try:
                summary = compute_kpi_series(
                    key=kpi_key,
                    role=user.role,
                    profile=target_profile,
                    settings=settings,
                    cache=cache,
                )
                if summary is not None:
                    prev_val = summary.previous_value
                    delta_pct = summary.delta_pct
                    series_warn = series_warning_for_summary(summary)
                    series_points = [
                        p.model_dump() if hasattr(p, "model_dump") else dict(p)
                        for p in summary.points
                    ]
            except (KpiComputationError, KpiForbidden, KpiNotFound, sa.exc.SQLAlchemyError):
                prev_val = None
                delta_pct = None
                series_points = []
                series_warn = None

        card = OverviewKpiCard(
            kpi_key=kpi_key,
            kpi_name=kpi_name,
            unit=unit,
            domain=domain,
            value=val if card_error is None else None,
            previous_value=prev_val if card_error is None else None,
            delta_pct=delta_pct if card_error is None else None,
            series=series_points if card_error is None else [],
            pinned=is_pinned,
            error=card_error,
            series_warning=series_warn if card_error is None else None,
        )
        cards.append(card)

    # 5. Open alerts and top alerts (deduplicated per rule_id, kpi_key, severity, is_acknowledged)
    alerts_stmt = sa.text("""
        WITH ranked AS (
            SELECT id, rule_id, kpi_key, severity, message, value, threshold,
                   is_acknowledged, acknowledged_by, acknowledged_at, created_at,
                   period, evidence, escalated_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY rule_id, kpi_key, severity, is_acknowledged
                       ORDER BY created_at DESC, id DESC
                   ) AS rn,
                   COUNT(*) OVER (
                       PARTITION BY rule_id, kpi_key, severity, is_acknowledged
                   ) AS occurrence_count
            FROM app.alert_event
            WHERE is_acknowledged = FALSE
        )
        SELECT id, rule_id, kpi_key, severity, message, value, threshold,
               is_acknowledged, acknowledged_by, acknowledged_at, created_at,
               period, evidence, escalated_at, occurrence_count
        FROM ranked
        WHERE rn = 1
        ORDER BY CASE WHEN severity IN ('nghiem_trong', 'critical') THEN 0 ELSE 1 END ASC,
                 created_at DESC, id DESC;
    """)
    with app_engine.connect() as conn:
        alert_rows = conn.execute(alerts_stmt).fetchall()

    open_alerts_counts = {"nghiem_trong": 0, "canh_bao": 0}
    filtered_alert_items: list[AlertItem] = []

    for r in alert_rows:
        if not can_access_kpi(user.role, r.kpi_key):
            continue

        sev = (r.severity or "").strip().lower()
        if sev in ("nghiem_trong", "critical"):
            open_alerts_counts["nghiem_trong"] += 1
        elif sev in ("canh_bao", "warning"):
            open_alerts_counts["canh_bao"] += 1

        filtered_alert_items.append(row_to_alert_item(r))

    top_alerts = filtered_alert_items[:3]

    # 6. Open actions count
    actions_stmt = sa.text("""
        SELECT id, kpi_key, assigned_role, created_by
        FROM app.action_item
        WHERE status IN ('open', 'in_progress');
    """)
    with app_engine.connect() as conn:
        action_rows = conn.execute(actions_stmt).fetchall()

    open_actions_count = 0
    for r in action_rows:
        if not can_access_kpi(user.role, r.kpi_key):
            continue
        if user.role == "ceo" or r.assigned_role == user.role or r.created_by == user.user_id:
            open_actions_count += 1

    # 7. Last alert job heartbeat
    heartbeat_stmt = sa.text("""
        SELECT created_at
        FROM app.job_heartbeat
        WHERE job_name = 'alert_engine' AND status = 'ok'
        ORDER BY created_at DESC, id DESC
        LIMIT 1;
    """)
    with app_engine.connect() as conn:
        hb_row = conn.execute(heartbeat_stmt).fetchone()

    last_alert_job_at = None
    if hb_row is not None and hb_row[0] is not None:
        hb_ts = hb_row[0]
        last_alert_job_at = hb_ts.isoformat() if isinstance(hb_ts, datetime) else str(hb_ts)

    # 8. Warnings
    warnings: list[str] = []
    if target_profile == "synth":
        warnings.append("SYNTHETIC_DATA")

    return OverviewResponse(
        greeting_title=greeting_title,
        data_profile=target_profile,
        as_of_date=as_of_str,
        last_alert_job_at=last_alert_job_at,
        open_alerts=open_alerts_counts,
        open_actions=open_actions_count,
        kpis=cards,
        top_alerts=top_alerts,
        suggested_questions=role_profile.suggested_questions,
        warnings=warnings,
    )
