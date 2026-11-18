"""Pinned KPIs CRUD router scoped by user and data profile.

Specifications:
- Spec §5.1 / P1r Task 2 (app.pinned_kpi)
- Plan Task 4 / Review Focus #3:
  - Unknown KPI checked first -> 404 KPI_NOT_FOUND
  - RBAC checked next -> 403 FORBIDDEN
  - Idempotent insert: 201 for new pin, 200 for existing pin without changing position
  - Scoped by user_id and data_profile (real vs synth)
  - GET filters out pins for KPIs where role has lost access
  - Exactly 1 audit log row written per request
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
import sqlalchemy as sa

from app.api.audit import write_audit_log
from app.api.deps import (
    ApiException,
    check_rate_limit,
    get_current_user,
    get_request_id,
    resolve_profile,
)
from app.api.schemas import (
    PinDeleteResponse,
    PinItem,
    PinListResponse,
    PinRequest,
)
from app.core.auth import UserPrincipal
from app.core.config import Settings, get_settings
from app.core.security import can_access_kpi
from app.knowledge.loader import get_kpi
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/pins", tags=["Pins"], dependencies=[Depends(check_rate_limit)])


@router.post("", response_model=PinItem, status_code=201)
def pin_kpi(
    payload: PinRequest,
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Pin a KPI to the user's dashboard (idempotent; 201 for new, 200 for already pinned)."""
    req_id = get_request_id(request)
    target_profile = resolve_profile(profile, settings, user=user)

    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
    audit_query = f"POST /v1/pins kpi={payload.kpi_key}"

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

    # 3. Idempotent insert or retrieve existing
    select_stmt = sa.text("""
        SELECT kpi_key, position, created_at
        FROM app.pinned_kpi
        WHERE user_id = :uid AND data_profile = :profile AND kpi_key = :kpi_key;
    """)

    with app_engine.begin() as conn:
        existing_row = conn.execute(
            select_stmt,
            {
                "uid": user.user_id,
                "profile": target_profile,
                "kpi_key": payload.kpi_key,
            },
        ).fetchone()

        if existing_row is not None:
            status_code = 200
            result_row = existing_row
        else:
            pos_stmt = sa.text("""
                SELECT COALESCE(MAX(position), 0) + 1 AS next_pos
                FROM app.pinned_kpi
                WHERE user_id = :uid AND data_profile = :profile;
            """)
            next_pos = conn.execute(
                pos_stmt,
                {
                    "uid": user.user_id,
                    "profile": target_profile,
                },
            ).scalar()

            insert_stmt = sa.text("""
                INSERT INTO app.pinned_kpi (user_id, data_profile, kpi_key, position, created_at)
                VALUES (:uid, :profile, :kpi_key, :pos, now())
                ON CONFLICT (user_id, data_profile, kpi_key) DO NOTHING
                RETURNING kpi_key, position, created_at;
            """)
            ins_row = conn.execute(
                insert_stmt,
                {
                    "uid": user.user_id,
                    "profile": target_profile,
                    "kpi_key": payload.kpi_key,
                    "pos": next_pos,
                },
            ).fetchone()

            if ins_row is not None:
                status_code = 201
                result_row = ins_row
            else:
                result_row = conn.execute(
                    select_stmt,
                    {
                        "uid": user.user_id,
                        "profile": target_profile,
                        "kpi_key": payload.kpi_key,
                    },
                ).fetchone()
                status_code = 200

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=audit_query,
    )

    warnings = ["SYNTHETIC_DATA"] if target_profile == "synth" else []
    created_str = (
        result_row.created_at.isoformat()
        if isinstance(result_row.created_at, datetime)
        else str(result_row.created_at)
    )
    pin_item = PinItem(
        kpi_key=result_row.kpi_key,
        position=result_row.position,
        created_at=created_str,
        warnings=warnings,
    )
    return JSONResponse(
        status_code=status_code,
        content=pin_item.model_dump(mode="json"),
    )


@router.get("", response_model=PinListResponse)
def list_pins(
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> PinListResponse:
    """Retrieve pinned KPIs scoped by user and profile, filtering out revoked permissions."""
    req_id = get_request_id(request)
    target_profile = resolve_profile(profile, settings, user=user)

    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
    audit_query = "GET /v1/pins"

    stmt = sa.text("""
        SELECT kpi_key, position, created_at
        FROM app.pinned_kpi
        WHERE user_id = :uid AND data_profile = :profile
        ORDER BY position ASC, id ASC;
    """)

    with app_engine.connect() as conn:
        rows = conn.execute(stmt, {"uid": user.user_id, "profile": target_profile}).fetchall()

    warnings = ["SYNTHETIC_DATA"] if target_profile == "synth" else []
    pins: list[PinItem] = []
    for r in rows:
        if not can_access_kpi(user.role, r.kpi_key):
            continue
        created_str = (
            r.created_at.isoformat()
            if isinstance(r.created_at, datetime)
            else str(r.created_at)
        )
        pins.append(
            PinItem(
                kpi_key=r.kpi_key,
                position=r.position,
                created_at=created_str,
                warnings=warnings,
            )
        )

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=audit_query,
    )

    return PinListResponse(pins=pins, total=len(pins), warnings=warnings)


@router.delete("/{kpi_key}", response_model=PinDeleteResponse)
def delete_pin(
    kpi_key: str,
    request: Request,
    profile: str | None = Query(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> PinDeleteResponse:
    """Remove a pinned KPI for the user and profile."""
    req_id = get_request_id(request)
    target_profile = resolve_profile(profile, settings, user=user)

    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile=target_profile))
    audit_query = f"DELETE /v1/pins/{kpi_key}"

    delete_stmt = sa.text("""
        DELETE FROM app.pinned_kpi
        WHERE user_id = :uid AND data_profile = :profile AND kpi_key = :kpi_key;
    """)

    with app_engine.begin() as conn:
        result = conn.execute(
            delete_stmt,
            {
                "uid": user.user_id,
                "profile": target_profile,
                "kpi_key": kpi_key,
            },
        )
        deleted_count = result.rowcount

    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=audit_query,
    )

    warnings = ["SYNTHETIC_DATA"] if target_profile == "synth" else []
    return PinDeleteResponse(deleted=deleted_count, warnings=warnings)
