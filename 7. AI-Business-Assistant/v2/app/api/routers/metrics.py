"""Metrics router for observability snapshot.

Specifications:
- Spec §5 T5, §11.7
- Access restricted to loopback/private hosts or roles {"ceo", "quan_tri_he_thong"}.
"""

import ipaddress
from typing import Any
from fastapi import APIRouter, Depends, Header, Request

from app.api.deps import ApiException, get_metrics, get_token_verifier
from app.core.auth import TokenAuthVerifier
from app.core.metrics import MetricsRegistry

router = APIRouter(tags=["Metrics"])

ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def _is_private_or_local(client_host: str) -> bool:
    """Check if client host is loopback, local test client, or private subnet (Docker 172.16.0.0/12, etc.)."""
    if client_host in ALLOWED_LOCAL_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(client_host)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False


@router.get("/metrics")
def get_system_metrics(
    request: Request,
    authorization: str | None = Header(default=None),
    verifier: TokenAuthVerifier = Depends(get_token_verifier),
    metrics: MetricsRegistry = Depends(get_metrics),
) -> dict[str, Any]:
    """Retrieve runtime latency, SQL validity, cache hit ratio, and request count snapshot."""
    client_host = request.client.host if request.client else "unknown"

    # Allow loopback/local test client or private networks
    is_local = _is_private_or_local(client_host)

    if not is_local:
        # Require admin or CEO role
        if not authorization or not authorization.startswith("Bearer "):
            raise ApiException(
                status_code=403,
                code="FORBIDDEN",
                message="Truy cập /metrics bị giới hạn đối với mạng nội bộ hoặc người dùng có thẩm quyền.",
            )
        try:
            token = authorization.split()[1]
            principal = verifier.verify_bearer_token(token)
            if principal.role not in ("ceo", "quan_tri_he_thong"):
                raise ApiException(
                    status_code=403,
                    code="FORBIDDEN",
                    message="Chỉ vai trò 'ceo' hoặc 'quan_tri_he_thong' mới được phép xem số liệu hệ thống.",
                )
        except Exception as e:
            if isinstance(e, ApiException):
                raise
            raise ApiException(status_code=403, code="FORBIDDEN", message=str(e)) from e

    return metrics.snapshot()
