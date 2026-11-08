"""Health and readiness probe routers.

Specifications:
- TC-T5-06: /ready returns 503 when PostgreSQL is unreachable
- Spec §5 T5, §11.7
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
import sqlalchemy as sa

from app.api.deps import get_ready_engine, get_request_id
from app.api.schemas import HealthResponse, ReadyResponse
from app.core.config import Settings, get_settings
from db.apply_db import get_app_engine
from sqlalchemy.engine import Engine

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Liveness probe: returns 200 OK if the process is up."""
    return HealthResponse(status="ok", version="2.0.0")


@router.get("/ready", response_model=ReadyResponse)
def readiness_check(
    request: Request,
    profile: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_ready_engine),
) -> JSONResponse | ReadyResponse:
    """Readiness probe: validates PostgreSQL database connectivity."""
    req_id = get_request_id(request)
    target_profile = (profile or settings.data_profile).strip().lower()

    try:
        target_engine = engine
        if profile and profile.strip().lower() != settings.data_profile.strip().lower():
            target_engine = get_app_engine(profile=target_profile)

        with target_engine.connect() as conn:
            conn.execute(sa.text("SELECT 1;"))

        return ReadyResponse(
            status="ready",
            db="up",
            profile=target_profile,
            details={"connected": True},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "db": "down",
                "profile": target_profile,
                "details": {"error": str(exc)},
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": f"Database is down or unreachable: {exc}",
                    "request_id": req_id,
                },
            },
        )
