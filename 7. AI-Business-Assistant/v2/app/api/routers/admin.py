"""Admin router for IAM user/session/audit management and monthly simulation runner.

Specifications:
- Design §5.4, §5.7, §5.8
- Plan Task 3
- Never expose password_hash or raw tokens, and never write secrets to app.audit_log or iam.auth_event.
"""

from datetime import date, datetime, timezone
import time

from fastapi import APIRouter, Body, Depends, Query, Request
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.api.audit import write_audit_log
from app.api.deps import (
    ApiException,
    get_current_user,
    get_iam_db_engine,
    get_kpi_cache,
    get_request_id,
)
from app.api.schemas import (
    AdminResetPasswordResponse,
    AdminRevokeSessionsResponse,
    AdminSessionDeleteResponse,
    AdminSessionItem,
    AdminSessionListResponse,
    AdminUserCreateRequest,
    AdminUserCreateResponse,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserUpdateRequest,
    AuthEventItem,
    AuthEventListResponse,
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationStatusResponse,
)
from app.core.auth import UserPrincipal
from app.core.cache import ScopedTTLCache
from app.core.config import Settings, get_settings
from app.core.errors import sanitize_db_error
from app.services import iam_service
from app.services.iam_service import (
    IamError,
    LastAdminProtectedError,
    PasswordPolicyError,
    SelfLockoutError,
    UserConflictError,
    UserNotFoundError,
)
from db.apply_db import get_app_engine
from db.synthetic.generate import DEFAULT_CHECKSUM_PATH, generate_synthetic_warehouse

router = APIRouter(prefix="/v1/admin", tags=["Admin"])


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _real_app_engine(settings: Settings) -> Engine:
    return get_app_engine(app_uri=settings.get_app_uri(profile="real"))


def _audit(
    settings: Settings,
    user: UserPrincipal,
    req_id: str,
    query: str,
    execution_time_ms: float = 0.0,
) -> None:
    write_audit_log(
        engine=_real_app_engine(settings),
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query=query,
        execution_time_ms=execution_time_ms,
    )


def require_admin_user(
    request: Request,
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> UserPrincipal:
    """Ensure the authenticated caller holds the quan_tri_he_thong role."""
    if user.role != "quan_tri_he_thong":
        req_id = get_request_id(request)
        _audit(
            settings,
            user,
            req_id,
            f"{request.method} {request.url.path} error_code=FORBIDDEN",
        )
        raise ApiException(
            status_code=403,
            code="FORBIDDEN",
            message="Chỉ Quản trị hệ thống mới được truy cập chức năng này.",
        )
    return user


@router.get("/users", response_model=AdminUserListResponse)
def list_admin_users(
    request: Request,
    q: str | None = Query(default=None),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> AdminUserListResponse:
    """List internal IAM accounts with optional search, role, and active filters."""
    req_id = get_request_id(request)
    rows = iam_service.list_users(iam_engine, q=q, role=role, is_active=is_active)
    _audit(settings, user, req_id, f"GET /v1/admin/users count={len(rows)}")
    items = [AdminUserItem(**row) for row in rows]
    return AdminUserListResponse(users=items, total=len(items))


@router.post("/users", response_model=AdminUserCreateResponse, status_code=201)
def create_admin_user(
    payload: AdminUserCreateRequest,
    request: Request,
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> AdminUserCreateResponse:
    """Create a new IAM user and return a one-time temporary password."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)
    uname_safe = (payload.username or "").strip().lower()

    try:
        created_user, temp_pw = iam_service.create_user(
            iam_engine,
            username=payload.username,
            display_name=payload.display_name,
            role=payload.role,
            allowed_profiles=list(payload.allowed_profiles) if payload.allowed_profiles is not None else None,
            email=payload.email,
            password=payload.password,
            must_change_password=payload.must_change_password,
            actor_user_id=user.user_id,
            client_ip=client_ip,
        )
    except UserConflictError as exc:
        _audit(settings, user, req_id, f"POST /v1/admin/users username={uname_safe} error_code=USER_CONFLICT")
        raise ApiException(status_code=409, code="USER_CONFLICT", message=str(exc)) from exc
    except PasswordPolicyError as exc:
        _audit(settings, user, req_id, f"POST /v1/admin/users username={uname_safe} error_code=PASSWORD_POLICY_ERROR")
        raise ApiException(status_code=422, code="PASSWORD_POLICY_ERROR", message=str(exc)) from exc
    except IamError as exc:
        _audit(settings, user, req_id, f"POST /v1/admin/users username={uname_safe} error_code=VALIDATION_ERROR")
        raise ApiException(status_code=422, code="VALIDATION_ERROR", message=str(exc)) from exc

    _audit(
        settings,
        user,
        req_id,
        f"POST /v1/admin/users user_id={created_user['user_id']} role={created_user['role']}",
    )
    return AdminUserCreateResponse(
        user=AdminUserItem(**created_user),
        temporary_password=temp_pw,
    )


@router.patch("/users/{user_id}", response_model=AdminUserItem)
def update_admin_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    request: Request,
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> AdminUserItem:
    """Update user profile, role, allowed_profiles, or active flag."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)

    try:
        updated_user = iam_service.update_user(
            iam_engine,
            user_id=user_id,
            actor_user_id=user.user_id,
            display_name=payload.display_name,
            email=payload.email,
            role=payload.role,
            allowed_profiles=list(payload.allowed_profiles) if payload.allowed_profiles is not None else None,
            is_active=payload.is_active,
            client_ip=client_ip,
        )
    except UserNotFoundError as exc:
        _audit(settings, user, req_id, f"PATCH /v1/admin/users/{user_id} error_code=USER_NOT_FOUND")
        raise ApiException(status_code=404, code="USER_NOT_FOUND", message=str(exc)) from exc
    except SelfLockoutError as exc:
        _audit(settings, user, req_id, f"PATCH /v1/admin/users/{user_id} error_code=SELF_LOCKOUT")
        raise ApiException(status_code=409, code="SELF_LOCKOUT", message=str(exc)) from exc
    except LastAdminProtectedError as exc:
        _audit(settings, user, req_id, f"PATCH /v1/admin/users/{user_id} error_code=LAST_ADMIN_PROTECTED")
        raise ApiException(status_code=409, code="LAST_ADMIN_PROTECTED", message=str(exc)) from exc
    except IamError as exc:
        _audit(settings, user, req_id, f"PATCH /v1/admin/users/{user_id} error_code=VALIDATION_ERROR")
        raise ApiException(status_code=422, code="VALIDATION_ERROR", message=str(exc)) from exc

    _audit(settings, user, req_id, f"PATCH /v1/admin/users/{user_id} role={updated_user['role']}")
    return AdminUserItem(**updated_user)


@router.post("/users/{user_id}/reset-password", response_model=AdminResetPasswordResponse)
def reset_admin_user_password(
    user_id: str,
    request: Request,
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> AdminResetPasswordResponse:
    """Reset a user's password to a generated one-time temporary password and revoke sessions."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)

    try:
        temp_pw = iam_service.reset_password_by_admin(
            iam_engine,
            user_id=user_id,
            actor_user_id=user.user_id,
            client_ip=client_ip,
        )
    except UserNotFoundError as exc:
        _audit(settings, user, req_id, f"POST /v1/admin/users/{user_id}/reset-password error_code=USER_NOT_FOUND")
        raise ApiException(status_code=404, code="USER_NOT_FOUND", message=str(exc)) from exc

    _audit(settings, user, req_id, f"POST /v1/admin/users/{user_id}/reset-password")
    return AdminResetPasswordResponse(user_id=user_id, temporary_password=temp_pw)


@router.post("/users/{user_id}/unlock", response_model=AdminUserItem)
def unlock_admin_user(
    user_id: str,
    request: Request,
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> AdminUserItem:
    """Clear login lockout state for a user."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)

    try:
        unlocked = iam_service.unlock_user(
            iam_engine,
            user_id=user_id,
            actor_user_id=user.user_id,
            client_ip=client_ip,
        )
    except UserNotFoundError as exc:
        _audit(settings, user, req_id, f"POST /v1/admin/users/{user_id}/unlock error_code=USER_NOT_FOUND")
        raise ApiException(status_code=404, code="USER_NOT_FOUND", message=str(exc)) from exc

    _audit(settings, user, req_id, f"POST /v1/admin/users/{user_id}/unlock")
    return AdminUserItem(**unlocked)


@router.post("/users/{user_id}/revoke-sessions", response_model=AdminRevokeSessionsResponse)
def revoke_admin_user_sessions(
    user_id: str,
    request: Request,
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> AdminRevokeSessionsResponse:
    """Immediately revoke all active sessions for the target user."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)

    try:
        revoked_count = iam_service.revoke_user_sessions(
            iam_engine,
            user_id=user_id,
            actor_user_id=user.user_id,
            reason="admin_revoked",
            client_ip=client_ip,
        )
    except UserNotFoundError as exc:
        _audit(settings, user, req_id, f"POST /v1/admin/users/{user_id}/revoke-sessions error_code=USER_NOT_FOUND")
        raise ApiException(status_code=404, code="USER_NOT_FOUND", message=str(exc)) from exc

    _audit(
        settings,
        user,
        req_id,
        f"POST /v1/admin/users/{user_id}/revoke-sessions revoked_count={revoked_count}",
    )
    return AdminRevokeSessionsResponse(user_id=user_id, revoked_count=revoked_count)


@router.get("/sessions", response_model=AdminSessionListResponse)
def list_admin_sessions(
    request: Request,
    user_id: str | None = Query(default=None),
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> AdminSessionListResponse:
    """List active sessions across the system or filtered by user_id."""
    req_id = get_request_id(request)
    rows = iam_service.list_active_sessions(iam_engine, user_id=user_id)
    _audit(settings, user, req_id, f"GET /v1/admin/sessions count={len(rows)}")
    items = [AdminSessionItem(**row) for row in rows]
    return AdminSessionListResponse(sessions=items, total=len(items))


@router.delete("/sessions/{session_id}", response_model=AdminSessionDeleteResponse)
def delete_admin_session(
    session_id: int,
    request: Request,
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> AdminSessionDeleteResponse:
    """Revoke a specific session immediately by session_id."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)

    revoked = iam_service.revoke_session(
        iam_engine,
        session_id=session_id,
        reason="admin_revoked",
        actor_user_id=user.user_id,
        client_ip=client_ip,
    )
    if not revoked:
        _audit(settings, user, req_id, f"DELETE /v1/admin/sessions/{session_id} error_code=SESSION_NOT_FOUND")
        raise ApiException(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message=f"Không tìm thấy phiên đăng nhập '{session_id}' hoặc phiên đã được thu hồi.",
        )

    _audit(settings, user, req_id, f"DELETE /v1/admin/sessions/{session_id}")
    return AdminSessionDeleteResponse(revoked=True)


@router.get("/auth-events", response_model=AuthEventListResponse)
def list_admin_auth_events(
    request: Request,
    user_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> AuthEventListResponse:
    """Query IAM authentication and administrative audit events."""
    req_id = get_request_id(request)
    rows = iam_service.list_auth_events(
        iam_engine,
        user_id=user_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    _audit(settings, user, req_id, f"GET /v1/admin/auth-events count={len(rows)}")
    items = [AuthEventItem(**row) for row in rows]
    return AuthEventListResponse(events=items, total=len(items))


def _write_simulation_heartbeat(
    app_engine: Engine,
    status: str,
    message: str,
    duration_ms: float,
) -> None:
    with app_engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO app.job_heartbeat (job_name, status, message, duration_ms, created_at) "
                "VALUES ('monthly_simulation', :status, :message, :duration_ms, now())"
            ),
            {
                "status": status[:50],
                "message": message,
                "duration_ms": float(duration_ms),
            },
        )


@router.get("/simulation/status", response_model=SimulationStatusResponse)
def get_simulation_status(
    request: Request,
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
) -> SimulationStatusResponse:
    """Return latest monthly simulation job heartbeat and EV-03 checksum presence."""
    req_id = get_request_id(request)
    app_engine = _real_app_engine(settings)

    with app_engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT status, message, created_at "
                "FROM app.job_heartbeat "
                "WHERE job_name = 'monthly_simulation' "
                "ORDER BY created_at DESC, id DESC LIMIT 1"
            )
        ).fetchone()

    last_run_at: str | None = None
    last_status: str | None = None
    last_message: str | None = None
    if row is not None:
        last_status = row.status
        last_message = row.message
        if row.created_at is not None:
            last_run_at = (
                row.created_at.isoformat()
                if isinstance(row.created_at, datetime)
                else str(row.created_at)
            )

    checksum_exists = DEFAULT_CHECKSUM_PATH.exists()
    _audit(settings, user, req_id, "GET /v1/admin/simulation/status")
    return SimulationStatusResponse(
        last_run_at=last_run_at,
        last_status=last_status,
        last_message=last_message,
        checksum_file_exists=checksum_exists,
    )


@router.post("/simulation/run", response_model=SimulationRunResponse)
def run_monthly_simulation(
    request: Request,
    payload: SimulationRunRequest = Body(default_factory=SimulationRunRequest),
    user: UserPrincipal = Depends(require_admin_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
    cache: ScopedTTLCache = Depends(get_kpi_cache),
) -> SimulationRunResponse:
    """Trigger deterministic synthetic warehouse regeneration, clear KPI cache, and record audit trail."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)
    app_engine = _real_app_engine(settings)

    start = time.perf_counter()
    try:
        checksums = generate_synthetic_warehouse(seed=payload.seed)
        cache.clear()
        duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
        run_at_iso = datetime.now(timezone.utc).isoformat()
        tables_generated = len(checksums)
        msg = f"Đã tạo lại {tables_generated} bảng dữ liệu mô phỏng (seed={payload.seed})."

        _write_simulation_heartbeat(app_engine, status="ok", message=msg, duration_ms=duration_ms)
        iam_service.record_auth_event(
            iam_engine,
            event_type="simulation_triggered",
            user_id=user.user_id,
            actor_user_id=user.user_id,
            detail={
                "seed": payload.seed,
                "tables_generated": tables_generated,
                "duration_ms": duration_ms,
                "status": "ok",
            },
            client_ip=client_ip,
        )
        _audit(
            settings,
            user,
            req_id,
            f"POST /v1/admin/simulation/run seed={payload.seed} tables={tables_generated}",
            execution_time_ms=duration_ms,
        )
        return SimulationRunResponse(
            status="ok",
            tables_generated=tables_generated,
            duration_ms=duration_ms,
            run_at=run_at_iso,
            message=msg,
        )
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
        clean_err = sanitize_db_error(str(exc))
        try:
            _write_simulation_heartbeat(app_engine, status="error", message=clean_err, duration_ms=duration_ms)
        except Exception:
            pass
        try:
            iam_service.record_auth_event(
                iam_engine,
                event_type="simulation_triggered",
                user_id=user.user_id,
                actor_user_id=user.user_id,
                detail={
                    "seed": payload.seed,
                    "duration_ms": duration_ms,
                    "status": "error",
                    "error": clean_err,
                },
                client_ip=client_ip,
            )
        except Exception:
            pass
        _audit(
            settings,
            user,
            req_id,
            f"POST /v1/admin/simulation/run seed={payload.seed} error_code=SIMULATION_FAILED",
            execution_time_ms=duration_ms,
        )
        raise ApiException(
            status_code=500,
            code="SIMULATION_FAILED",
            message=f"Chạy mô phỏng dữ liệu tháng thất bại: {clean_err}",
        ) from exc
