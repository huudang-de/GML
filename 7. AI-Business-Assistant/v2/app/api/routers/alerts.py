"""Alert management and acknowledgment router with strict RBAC filtering.

Specifications:
- Review Focus #5: Alert retrieval filtered by allowed views; unauthorized ack returns 403.
- Spec §5 T5, §11.7
"""

from datetime import datetime, timezone
import json
from typing import Any, Literal
from fastapi import APIRouter, Depends, Query, Request
import sqlalchemy as sa

from app.api.audit import write_audit_log
from app.api.deps import (
    ApiException,
    check_rate_limit,
    get_current_user,
    get_request_id,
)
from app.api.schemas import AlertAckResponse, AlertItem, AlertListResponse
from app.core.auth import UserPrincipal
from app.core.config import Settings, get_settings
from app.core.security import can_access_kpi, kpi_domain
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/alerts", tags=["Alerts"], dependencies=[Depends(check_rate_limit)])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    request: Request,
    domain: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: Literal["open", "acked"] | None = Query(default=None),
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> AlertListResponse:
    """Retrieve operational alerts strictly filtered by caller's role permissions (Review Focus #5)."""
    req_id = get_request_id(request)
    target_profile = (profile or settings.data_profile).strip().lower()
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))

    where_clauses: list[str] = []
    params: dict[str, Any] = {}

    if status == "open":
        where_clauses.append("is_acknowledged = FALSE")
    elif status == "acked":
        where_clauses.append("is_acknowledged = TRUE")

    if severity is not None:
        sev_norm = severity.strip().lower()
        if sev_norm in ("canh_bao", "warning"):
            where_clauses.append("severity IN ('canh_bao', 'warning')")
        elif sev_norm in ("nghiem_trong", "critical"):
            where_clauses.append("severity IN ('nghiem_trong', 'critical')")
        else:
            where_clauses.append("severity = :severity")
            params["severity"] = severity

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    stmt = sa.text(f"""
        SELECT id, rule_id, kpi_key, severity, message, value, threshold,
               is_acknowledged, acknowledged_by, acknowledged_at, created_at,
               period, evidence, escalated_at
        FROM app.alert_event
        {where_sql}
        ORDER BY is_acknowledged ASC,
                 CASE WHEN severity IN ('nghiem_trong', 'critical') THEN 0 ELSE 1 END ASC,
                 created_at DESC, id DESC
        LIMIT 100;
    """)

    with app_engine.connect() as conn:
        rows = conn.execute(stmt, params).fetchall()

    items: list[AlertItem] = []
    for r in rows:
        if not can_access_kpi(user.role, r.kpi_key):
            continue  # Strictly hide unauthorized alert

        # Critical Ruling #2 (uncatalogued alerts):
        try:
            row_domain = kpi_domain(r.kpi_key)
        except (KeyError, ValueError):
            row_domain = None

        if domain is not None and row_domain != domain:
            continue

        created_str = r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at)
        ack_str = r.acknowledged_at.isoformat() if isinstance(r.acknowledged_at, datetime) else (str(r.acknowledged_at) if r.acknowledged_at else None)
        esc_str = r.escalated_at.isoformat() if isinstance(r.escalated_at, datetime) else (str(r.escalated_at) if r.escalated_at else None)

        raw_ev = r.evidence
        if isinstance(raw_ev, str):
            try:
                ev_dict = json.loads(raw_ev)
            except Exception:
                ev_dict = None
        elif isinstance(raw_ev, dict):
            ev_dict = raw_ev
        else:
            ev_dict = None

        items.append(
            AlertItem(
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
            )
        )

    warnings: list[str] = ["SYNTHETIC_DATA"] if target_profile == "synth" else []

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query="GET /v1/alerts",
    )

    return AlertListResponse(alerts=items, total=len(items), warnings=warnings)


@router.post("/{alert_id}/ack", response_model=AlertAckResponse)
def acknowledge_alert(
    alert_id: int,
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> AlertAckResponse:
    """Acknowledge an operational alert (enforces 403 on unauthorized view domain)."""
    req_id = get_request_id(request)
    target_profile = (profile or settings.data_profile).strip().lower()
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))

    # 1. Fetch alert
    select_stmt = sa.text("""
        SELECT id, kpi_key, is_acknowledged
        FROM app.alert_event
        WHERE id = :id;
    """)
    with app_engine.connect() as conn:
        alert_row = conn.execute(select_stmt, {"id": alert_id}).fetchone()

    if not alert_row:
        raise ApiException(
            status_code=404,
            code="ALERT_NOT_FOUND",
            message=f"Cảnh báo ID {alert_id} không tồn tại.",
        )

    # 2. Check RBAC for this alert's KPI
    if not can_access_kpi(user.role, alert_row.kpi_key):
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=f"POST /v1/alerts/{alert_id}/ack",
        )
        raise ApiException(
            status_code=403,
            code="FORBIDDEN",
            message=f"Vai trò '{user.role}' không có quyền xác nhận cảnh báo trên KPI '{alert_row.kpi_key}'.",
        )

    # 3. Update alert acknowledgment
    ack_now = datetime.now(timezone.utc)
    update_stmt = sa.text("""
        UPDATE app.alert_event
        SET is_acknowledged = true,
            acknowledged_by = :user_id,
            acknowledged_at = :now
        WHERE id = :id;
    """)
    with app_engine.begin() as conn:
        conn.execute(
            update_stmt,
            {
                "id": alert_id,
                "user_id": user.user_id,
                "now": ack_now,
            },
        )

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=f"POST /v1/alerts/{alert_id}/ack",
    )

    return AlertAckResponse(
        id=alert_id,
        is_acknowledged=True,
        acknowledged_by=user.user_id,
        acknowledged_at=ack_now.isoformat(),
    )
