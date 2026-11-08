"""Alert management and acknowledgment router with strict RBAC filtering.

Specifications:
- Review Focus #5: Alert retrieval filtered by allowed views; unauthorized ack returns 403.
- Spec §5 T5, §11.7
"""

from datetime import datetime, timezone
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
from app.core.security import get_allowed_views
from app.knowledge.loader import get_kpi
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/alerts", tags=["Alerts"], dependencies=[Depends(check_rate_limit)])


def _user_can_access_kpi(role: str, kpi_key: str) -> bool:
    """Check if role has access to view/ack alerts for a given KPI key."""
    try:
        kpi_def = get_kpi(kpi_key)
        required_views = set(kpi_def.nguon_view)
        allowed_views = get_allowed_views(role)
        return required_views.issubset(allowed_views)
    except KeyError:
        return role in ("ceo", "quan_tri_he_thong")


@router.get("", response_model=AlertListResponse)
def list_alerts(
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> AlertListResponse:
    """Retrieve operational alerts strictly filtered by caller's role permissions (Review Focus #5)."""
    req_id = get_request_id(request)
    target_profile = (profile or settings.data_profile).strip().lower()
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))

    stmt = sa.text("""
        SELECT id, rule_id, kpi_key, severity, message, value, threshold,
               is_acknowledged, acknowledged_by, acknowledged_at, created_at
        FROM app.alert_event
        ORDER BY created_at DESC, id DESC
        LIMIT 100;
    """)

    with app_engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()

    items: list[AlertItem] = []
    for r in rows:
        if not _user_can_access_kpi(user.role, r.kpi_key):
            continue  # Strictly hide unauthorized alert

        created_str = r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at)
        ack_str = r.acknowledged_at.isoformat() if isinstance(r.acknowledged_at, datetime) else (str(r.acknowledged_at) if r.acknowledged_at else None)

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
            )
        )

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query="GET /v1/alerts",
    )

    return AlertListResponse(alerts=items, total=len(items))


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
    if not _user_can_access_kpi(user.role, alert_row.kpi_key):
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
