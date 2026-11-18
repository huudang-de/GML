"""Action items CRUD router with approved-action validation, RBAC, and audit logging.

Specifications:
- Spec §5.1 / P1r Task 2 (app.action_item)
- Spec §5 T3 (DecisionAdvisor & approved actions allowlist)
- Plan Task 3 / Review Focus #1 & #2:
  - Unknown KPI checked first -> 404 KPI_NOT_FOUND
  - RBAC checked next -> 403 FORBIDDEN
  - Source existence + ownership + KPI scope checked -> 404 SOURCE_NOT_FOUND
  - Approved action allowlist checked -> 422 ACTION_NOT_APPROVED
  - Unique constraint (source_type, source_ref, title) -> 409 ACTION_DUPLICATE
  - Strict visibility on GET & PATCH (can_access_kpi AND (ceo OR assigned_role OR created_by))
  - Never include title or note in audit log query metadata!
"""

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
import sqlalchemy as sa

from app.agents.advisor import resolve_approved_action
from app.api.audit import write_audit_log
from app.api.deps import (
    ApiException,
    check_rate_limit,
    get_current_user,
    get_request_id,
    resolve_profile,
)
from app.api.schemas import (
    ActionCreateRequest,
    ActionItem,
    ActionListResponse,
    ActionUpdateRequest,
)
from app.core.auth import UserPrincipal
from app.core.config import Settings, get_settings
from app.core.security import can_access_kpi, kpi_domain
from app.knowledge.loader import get_kpi
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/actions", tags=["Actions"], dependencies=[Depends(check_rate_limit)])


def _is_action_visible(user: UserPrincipal, kpi_key: str, assigned_role: str, created_by: str) -> bool:
    """Enforce visibility rule: can_access_kpi AND (role == ceo OR assigned_role == role OR created_by == user_id)."""
    if not can_access_kpi(user.role, kpi_key):
        return False
    return (
        user.role == "ceo"
        or assigned_role == user.role
        or created_by == user.user_id
    )


def _row_to_action_item(row: Any, warnings: list[str]) -> ActionItem:
    """Convert a database row into an ActionItem schema object."""
    try:
        domain = kpi_domain(row.kpi_key)
    except (KeyError, ValueError):
        domain = "khac"

    created_str = row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at)
    updated_str = row.updated_at.isoformat() if isinstance(row.updated_at, datetime) else str(row.updated_at)

    return ActionItem(
        id=row.id,
        title=row.title,
        kpi_key=row.kpi_key,
        level=row.level,
        domain=domain,
        source_type=row.source_type,
        source_ref=row.source_ref,
        assigned_role=row.assigned_role,
        status=row.status,
        due_date=row.due_date,
        note=row.note,
        created_by=row.created_by,
        created_at=created_str,
        updated_at=updated_str,
        warnings=warnings,
    )


@router.post("", response_model=ActionItem, status_code=201)
def create_action(
    payload: ActionCreateRequest,
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ActionItem:
    """Create an operational action item from an alert or chat turn."""
    req_id = get_request_id(request)
    target_profile = resolve_profile(profile, settings, user=user)
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))

    # Audit privacy constraint: NEVER include title or note in audit log query!
    audit_query = f"POST /v1/actions kpi={payload.kpi_key} source={payload.source_type}:{payload.source_ref}"

    # 1. Check KPI existence first (Ruling #3)
    try:
        get_kpi(payload.kpi_key)
    except KeyError:
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=audit_query,
        )
        raise ApiException(
            status_code=404,
            code="KPI_NOT_FOUND",
            message=f"Chỉ số '{payload.kpi_key}' không tồn tại trong hệ thống.",
        )

    # 2. Check RBAC next
    if not can_access_kpi(user.role, payload.kpi_key):
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=audit_query,
        )
        raise ApiException(
            status_code=403,
            code="FORBIDDEN",
            message=f"Vai trò '{user.role}' không có quyền truy cập chỉ số '{payload.kpi_key}'.",
        )

    # 3. Check source existence and scope
    if payload.source_type == "alert":
        try:
            alert_id = int(payload.source_ref)
        except ValueError:
            write_audit_log(
                engine=app_engine,
                user_id=user.user_id,
                role=user.role,
                request_id=req_id,
                query=audit_query,
            )
            raise ApiException(
                status_code=404,
                code="SOURCE_NOT_FOUND",
                message=f"Nguồn cảnh báo '{payload.source_ref}' không hợp lệ hoặc không tồn tại.",
            )

        stmt = sa.text("SELECT id, kpi_key FROM app.alert_event WHERE id = :aid AND kpi_key = :kpi_key")
        with app_engine.connect() as conn:
            alert_row = conn.execute(stmt, {"aid": alert_id, "kpi_key": payload.kpi_key}).fetchone()

        if not alert_row:
            write_audit_log(
                engine=app_engine,
                user_id=user.user_id,
                role=user.role,
                request_id=req_id,
                query=audit_query,
            )
            raise ApiException(
                status_code=404,
                code="SOURCE_NOT_FOUND",
                message=f"Cảnh báo ID {alert_id} với KPI '{payload.kpi_key}' không tồn tại.",
            )

    elif payload.source_type == "chat":
        stmt = sa.text("""
            SELECT request_id, user_id, kpi_keys
            FROM app.chat_turn
            WHERE request_id = :rid AND user_id = :uid
        """)
        with app_engine.connect() as conn:
            chat_row = conn.execute(stmt, {"rid": payload.source_ref, "uid": user.user_id}).fetchone()

        if not chat_row:
            write_audit_log(
                engine=app_engine,
                user_id=user.user_id,
                role=user.role,
                request_id=req_id,
                query=audit_query,
            )
            raise ApiException(
                status_code=404,
                code="SOURCE_NOT_FOUND",
                message=f"Lượt trao đổi chat '{payload.source_ref}' không tồn tại hoặc không thuộc quyền sở hữu.",
            )

        turn_kpis = chat_row.kpi_keys or []
        if payload.kpi_key not in turn_kpis:
            write_audit_log(
                engine=app_engine,
                user_id=user.user_id,
                role=user.role,
                request_id=req_id,
                query=audit_query,
            )
            raise ApiException(
                status_code=404,
                code="SOURCE_NOT_FOUND",
                message=f"Lượt chat không chứa thông tin về chỉ số '{payload.kpi_key}'.",
            )

    # 4. Check approved action allowlist
    resolved = resolve_approved_action(payload.kpi_key, payload.level, payload.title)
    if resolved is None:
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=audit_query,
        )
        raise ApiException(
            status_code=422,
            code="ACTION_NOT_APPROVED",
            message=f"Hành động '{payload.title}' không nằm trong danh mục hành động được phê duyệt cho KPI '{payload.kpi_key}' mức '{payload.level}'.",
        )

    canonical_title, authority_role = resolved

    # 5. Insert into app.action_item
    insert_stmt = sa.text("""
        INSERT INTO app.action_item (
            title, kpi_key, level, source_type, source_ref, assigned_role,
            status, due_date, note, created_by, created_at, updated_at
        ) VALUES (
            :title, :kpi_key, :level, :source_type, :source_ref, :assigned_role,
            'open', :due_date, :note, :created_by, now(), now()
        )
        RETURNING id, title, kpi_key, level, source_type, source_ref,
                  assigned_role, status, due_date, note, created_by,
                  created_at, updated_at;
    """)

    try:
        with app_engine.begin() as conn:
            inserted_row = conn.execute(
                insert_stmt,
                {
                    "title": canonical_title,
                    "kpi_key": payload.kpi_key,
                    "level": payload.level,
                    "source_type": payload.source_type,
                    "source_ref": payload.source_ref,
                    "assigned_role": authority_role,
                    "due_date": payload.due_date,
                    "note": payload.note,
                    "created_by": user.user_id,
                },
            ).fetchone()
    except sa.exc.IntegrityError:
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=audit_query,
        )
        raise ApiException(
            status_code=409,
            code="ACTION_DUPLICATE",
            message=f"Hành động '{canonical_title}' cho nguồn '{payload.source_type}:{payload.source_ref}' đã tồn tại.",
        )

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=audit_query,
    )

    warnings = ["SYNTHETIC_DATA"] if target_profile == "synth" else []
    return _row_to_action_item(inserted_row, warnings=warnings)


@router.get("", response_model=ActionListResponse)
def list_actions(
    request: Request,
    status: Literal["open", "in_progress", "done", "dismissed"] | None = Query(default=None),
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ActionListResponse:
    """List operational action items filtered by role visibility and optional status."""
    req_id = get_request_id(request)
    target_profile = resolve_profile(profile, settings, user=user)
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))

    where_clauses: list[str] = []
    params: dict[str, Any] = {}

    if status is not None:
        where_clauses.append("status = :status")
        params["status"] = status

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    stmt = sa.text(f"""
        SELECT id, title, kpi_key, level, source_type, source_ref,
               assigned_role, status, due_date, note, created_by,
               created_at, updated_at
        FROM app.action_item
        {where_sql}
        ORDER BY created_at DESC, id DESC;
    """)

    with app_engine.connect() as conn:
        rows = conn.execute(stmt, params).fetchall()

    warnings = ["SYNTHETIC_DATA"] if target_profile == "synth" else []
    items: list[ActionItem] = []
    for r in rows:
        if not _is_action_visible(user, r.kpi_key, r.assigned_role, r.created_by):
            continue
        items.append(_row_to_action_item(r, warnings=warnings))

    audit_query = f"GET /v1/actions status={status}" if status else "GET /v1/actions"
    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=audit_query,
    )

    return ActionListResponse(actions=items, total=len(items), warnings=warnings)


@router.patch("/{action_id}", response_model=ActionItem)
def update_action(
    action_id: int,
    payload: ActionUpdateRequest,
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ActionItem:
    """Update action item status or note (enforces visibility; returns 404 if unauthorized)."""
    req_id = get_request_id(request)
    target_profile = resolve_profile(profile, settings, user=user)
    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
    audit_query = f"PATCH /v1/actions/{action_id}"

    # 1. Fetch current action item
    stmt = sa.text("""
        SELECT id, title, kpi_key, level, source_type, source_ref,
               assigned_role, status, due_date, note, created_by,
               created_at, updated_at
        FROM app.action_item
        WHERE id = :id;
    """)
    with app_engine.connect() as conn:
        row = conn.execute(stmt, {"id": action_id}).fetchone()

    # 2. Check existence and visibility (404 without leaking existence)
    if not row or not _is_action_visible(user, row.kpi_key, row.assigned_role, row.created_by):
        write_audit_log(
            engine=app_engine,
            user_id=user.user_id,
            role=user.role,
            request_id=req_id,
            query=audit_query,
        )
        raise ApiException(
            status_code=404,
            code="ACTION_NOT_FOUND",
            message=f"Hành động ID {action_id} không tồn tại hoặc không có quyền truy cập.",
        )

    # 3. Update status / note / updated_at
    update_clauses = ["updated_at = now()"]
    params: dict[str, Any] = {"id": action_id}

    if "status" in payload.model_fields_set and payload.status is not None:
        update_clauses.append("status = :status")
        params["status"] = payload.status

    if "note" in payload.model_fields_set:
        update_clauses.append("note = :note")
        params["note"] = payload.note

    update_stmt = sa.text(f"""
        UPDATE app.action_item
        SET {", ".join(update_clauses)}
        WHERE id = :id
        RETURNING id, title, kpi_key, level, source_type, source_ref,
                  assigned_role, status, due_date, note, created_by,
                  created_at, updated_at;
    """)

    with app_engine.begin() as conn:
        updated_row = conn.execute(update_stmt, params).fetchone()

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=audit_query,
    )

    warnings = ["SYNTHETIC_DATA"] if target_profile == "synth" else []
    return _row_to_action_item(updated_row, warnings=warnings)
