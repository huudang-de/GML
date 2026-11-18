"""Authentication router for login, logout, current user identity, and password change.

Specifications:
- Design §5.3, §5.4
- Plan Task 2
- Never log raw passwords or raw bearer tokens in audit_log or auth_event.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.engine import Engine

from app.api.audit import write_audit_log
from app.api.deps import (
    ApiException,
    get_current_user,
    get_iam_db_engine,
    get_login_rate_limiter,
    get_request_id,
)
from app.api.schemas import (
    AuthenticatedUserInfo,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
)
from app.core.auth import UserPrincipal
from app.core.config import Settings, get_settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.services import iam_service
from app.services.iam_service import (
    AccountLockedError,
    InvalidCredentialsError,
    PasswordPolicyError,
    UserNotFoundError,
)
from db.apply_db import get_app_engine

router = APIRouter(prefix="/v1/auth", tags=["Auth"])


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    limiter: SlidingWindowRateLimiter = Depends(get_login_rate_limiter),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> LoginResponse:
    """Authenticate username/password and issue a stateful SHA-256-backed bearer token."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)

    allowed, _ = limiter.check(client_ip)
    if not allowed:
        raise ApiException(
            status_code=429,
            code="RATE_LIMITED",
            message="Quá nhiều lần thử đăng nhập từ địa chỉ IP này. Vui lòng thử lại sau 1 phút.",
        )

    try:
        user_dict = iam_service.authenticate_user(
            iam_engine,
            username=payload.username,
            password=payload.password,
            client_ip=client_ip,
        )
    except InvalidCredentialsError as exc:
        raise ApiException(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message=str(exc),
        ) from exc
    except AccountLockedError as exc:
        locked_iso = exc.locked_until.isoformat()
        raise ApiException(
            status_code=423,
            code="ACCOUNT_LOCKED",
            message=f"{exc} Tài khoản sẽ mở khoá lúc {locked_iso}.",
            details={"locked_until": locked_iso},
        ) from exc

    user_agent = request.headers.get("user-agent")
    raw_token, session_rec = iam_service.create_session(
        iam_engine,
        user_id=user_dict["user_id"],
        client_ip=client_ip,
        user_agent=user_agent,
    )

    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile="real"))
    write_audit_log(
        engine=app_engine,
        user_id=user_dict["user_id"],
        role=user_dict["role"],
        request_id=req_id,
        query=f"POST /v1/auth/login username={user_dict['username']}",
    )

    exp_dt = session_rec["expires_at"]
    expires_at_iso = exp_dt.isoformat() if isinstance(exp_dt, datetime) else str(exp_dt)

    return LoginResponse(
        access_token=raw_token,
        token_type="bearer",
        expires_at=expires_at_iso,
        user=AuthenticatedUserInfo(
            user_id=user_dict["user_id"],
            username=user_dict.get("username"),
            display_name=user_dict["display_name"],
            email=user_dict.get("email"),
            role=user_dict["role"],
            allowed_profiles=list(user_dict.get("allowed_profiles") or ["real"]),
            must_change_password=bool(user_dict.get("must_change_password", False)),
        ),
    )


@router.post("/logout")
def logout(
    request: Request,
    authorization: str | None = Header(default=None),
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> dict[str, str]:
    """Revoke the active bearer session immediately and audit the logout."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)

    raw_token: str | None = None
    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_token = parts[1]

    if user.session_id is not None:
        iam_service.revoke_session(
            iam_engine,
            session_id=user.session_id,
            reason="user_logout",
            actor_user_id=user.user_id,
            client_ip=client_ip,
        )
    elif raw_token:
        iam_service.revoke_session(
            iam_engine,
            raw_token=raw_token,
            reason="user_logout",
            actor_user_id=user.user_id,
            client_ip=client_ip,
        )

    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile="real"))
    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query="POST /v1/auth/logout",
    )

    return {"status": "ok"}


@router.get("/me", response_model=AuthenticatedUserInfo)
def get_me(
    user: UserPrincipal = Depends(get_current_user),
) -> AuthenticatedUserInfo:
    """Return the authenticated caller's identity, role, and profile permissions."""
    return AuthenticatedUserInfo(
        user_id=user.user_id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        role=user.role,
        allowed_profiles=list(user.allowed_profiles or ["real"]),
        must_change_password=bool(user.must_change_password),
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    user: UserPrincipal = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    iam_engine: Engine = Depends(get_iam_db_engine),
) -> ChangePasswordResponse:
    """Change current user password, lift must_change_password gate, and revoke other sessions."""
    req_id = get_request_id(request)
    client_ip = _client_ip(request)

    try:
        iam_service.change_user_password(
            iam_engine,
            user_id=user.user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
            keep_session_id=user.session_id,
            client_ip=client_ip,
        )
    except InvalidCredentialsError as exc:
        raise ApiException(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message=str(exc),
        ) from exc
    except PasswordPolicyError as exc:
        raise ApiException(
            status_code=422,
            code="PASSWORD_POLICY_ERROR",
            message=str(exc),
        ) from exc
    except UserNotFoundError as exc:
        raise ApiException(
            status_code=404,
            code="USER_NOT_FOUND",
            message=str(exc),
        ) from exc

    app_engine = get_app_engine(app_uri=settings.get_app_uri(profile="real"))
    write_audit_log(
        engine=app_engine,
        user_id=user.user_id,
        role=user.role,
        request_id=req_id,
        query="POST /v1/auth/change-password",
    )

    return ChangePasswordResponse(
        status="ok",
        message="Đổi mật khẩu thành công.",
    )
