"""Alert management and acknowledgment router with strict RBAC filtering.

Specifications:
- Review Focus #5: Alert retrieval filtered by allowed views; unauthorized ack returns 403.
- Spec §5 T5, §11.7
"""

from datetime import datetime, timezone
from typing import Any, Literal
from fastapi import APIRouter, Depends, Query, Request
import sqlalchemy as sa

from app.api.audit import write_audit_log
from app.api.deps import (
    ApiException,
    check_rate_limit,
    get_current_user,
    get_request_id,
    resolve_profile,
)
from app.api.schemas import AlertAckResponse, AlertItem, AlertListResponse
from app.core.auth import UserPrincipal
from app.core.config import Settings, get_settings
from app.core.security import can_access_kpi
from app.services.briefing import row_to_alert_item
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/alerts", tags=["Alerts"], dependencies=[Depends(check_rate_limit)])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    request: Request,
    domain: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: Literal["open", "acked"] | None = Query(default=None),
    profile: str | None = Query(default=None),
    dedup: bool = Query(default=True),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> AlertListResponse:
    """Retrieve operational alerts strictly filtered by caller's role permissions (Review Focus #5)."""
    req_id = get_request_id(request)
    target_profile = resolve_profile(profile, settings)
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

    if dedup:
        stmt = sa.text(f"""
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
                {where_sql}
            )
            SELECT id, rule_id, kpi_key, severity, message, value, threshold,
                   is_acknowledged, acknowledged_by, acknowledged_at, created_at,
                   period, evidence, escalated_at, occurrence_count
            FROM ranked
            WHERE rn = 1
            ORDER BY is_acknowledged ASC,
                     CASE WHEN severity IN ('nghiem_trong', 'critical') THEN 0 ELSE 1 END ASC,
                     created_at DESC, id DESC
            LIMIT 100;
        """)
    else:
        stmt = sa.text(f"""
            SELECT id, rule_id, kpi_key, severity, message, value, threshold,
                   is_acknowledged, acknowledged_by, acknowledged_at, created_at,
                   period, evidence, escalated_at,
                   1 AS occurrence_count
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

        alert_item = row_to_alert_item(r)
        if domain is not None and alert_item.domain != domain:
            continue

        items.append(alert_item)

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
    target_profile = resolve_profile(profile, settings)
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))

    # 1. Fetch alert
    select_stmt = sa.text("""
        SELECT id, rule_id, kpi_key, severity, is_acknowledged
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

    # 3. Update alert acknowledgment (including unacknowledged siblings in same dedup group)
    ack_now = datetime.now(timezone.utc)
    update_stmt = sa.text("""
        UPDATE app.alert_event
        SET is_acknowledged = true,
            acknowledged_by = :user_id,
            acknowledged_at = :now
        WHERE id = :id
           OR (
               is_acknowledged = FALSE
               AND rule_id IS NOT DISTINCT FROM :rule_id
               AND kpi_key = :kpi_key
               AND severity = :severity
           );
    """)
    with app_engine.begin() as conn:
        conn.execute(
            update_stmt,
            {
                "id": alert_id,
                "rule_id": alert_row.rule_id,
                "kpi_key": alert_row.kpi_key,
                "severity": alert_row.severity,
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
