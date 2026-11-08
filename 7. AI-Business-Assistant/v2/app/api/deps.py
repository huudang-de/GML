"""FastAPI dependencies, exception types, and security providers.

Specifications:
- TC-T5-02, TC-T5-04, TC-T5-05
- Spec §5 T5, §11.7
- Unified Error Envelope
"""

from functools import lru_cache
import uuid
from fastapi import Header, HTTPException, Request, Depends
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.core.config import Settings, get_settings
from app.core.auth import TokenAuthVerifier, UserPrincipal, AuthenticationError
from app.core.cache import ScopedTTLCache
from app.core.logging import request_id_ctx
from app.core.metrics import MetricsRegistry, get_metrics_registry
from app.core.rate_limit import SlidingWindowRateLimiter
from db.apply_db import get_app_engine, get_ro_engine


class ApiException(HTTPException):
    """Custom API exception supporting the unified error envelope."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details or {}


# Global singletons
_RATE_LIMITER: SlidingWindowRateLimiter | None = None
_KPI_CACHE: ScopedTTLCache | None = None


def reset_rate_limiter() -> None:
    """Reset global rate limiter singleton (for test isolation)."""
    global _RATE_LIMITER
    _RATE_LIMITER = None


def reset_kpi_cache() -> None:
    """Reset global KPI cache singleton (for test isolation)."""
    global _KPI_CACHE
    _KPI_CACHE = None


def get_token_verifier(settings: Settings = Depends(get_settings)) -> TokenAuthVerifier:
    """Return configured TokenAuthVerifier."""
    return TokenAuthVerifier(settings)


def get_rate_limiter(settings: Settings = Depends(get_settings)) -> SlidingWindowRateLimiter:
    """Return singleton SlidingWindowRateLimiter."""
    global _RATE_LIMITER
    if _RATE_LIMITER is None:
        _RATE_LIMITER = SlidingWindowRateLimiter(
            max_requests=settings.rate_limit_per_minute,
            window_seconds=60,
        )
    return _RATE_LIMITER


def get_kpi_cache(settings: Settings = Depends(get_settings)) -> ScopedTTLCache:
    """Return singleton ScopedTTLCache."""
    global _KPI_CACHE
    if _KPI_CACHE is None:
        _KPI_CACHE = ScopedTTLCache(
            ttl_seconds=settings.kpi_cache_ttl_seconds,
            max_entries=512,
        )
    return _KPI_CACHE


def get_metrics() -> MetricsRegistry:
    """Return singleton MetricsRegistry."""
    return get_metrics_registry()


def get_ready_engine(settings: Settings = Depends(get_settings)) -> Engine:
    """Return database engine for health/readiness check."""
    return get_app_engine(app_uri=settings.get_app_uri())


def get_request_id(request: Request) -> str:
    """Extract or generate unique request_id and update contextvar."""
    if hasattr(request.state, "request_id") and request.state.request_id:
        req_id = request.state.request_id
    else:
        req_id = request.headers.get("x-request-id")
        if not req_id or not req_id.strip():
            req_id = f"req-{uuid.uuid4().hex[:12]}"
        else:
            req_id = req_id.strip()
        request.state.request_id = req_id

    request_id_ctx.set(req_id)
    return req_id


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    verifier: TokenAuthVerifier = Depends(get_token_verifier),
) -> UserPrincipal:
    """Authenticate bearer token and resolve UserPrincipal."""
    req_id = get_request_id(request)

    if not authorization or not authorization.strip():
        raise ApiException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Thiếu thông tin xác thực Bearer token trong header Authorization.",
        )

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ApiException(
            status_code=401,
            code="UNAUTHORIZED",
            message="Header Authorization phải có định dạng: Bearer <token>.",
        )

    raw_token = parts[1]
    try:
        return verifier.verify_bearer_token(raw_token)
    except AuthenticationError as e:
        raise ApiException(
            status_code=e.status_code,
            code="UNAUTHORIZED",
            message=e.message,
        ) from e


def check_rate_limit(
    user: UserPrincipal = Depends(get_current_user),
    limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
) -> None:
    """Enforce per-user sliding window rate limiting."""
    allowed, remaining = limiter.check(user.user_id)
    if not allowed:
        raise ApiException(
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            message=f"Quá giới hạn tần suất yêu cầu cho người dùng '{user.user_id}'. Vui lòng thử lại sau.",
        )
