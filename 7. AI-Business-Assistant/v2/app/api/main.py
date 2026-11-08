"""FastAPI Application Factory, Gateway Middleware, and Central Exception Handling.

Specifications:
- TC-T5-01..09
- Unified Error Envelope: {"error": {"code": str, "message": str, "request_id": str}}
- Review Focus #4: Trapping RequestValidationError (422) with X-Request-ID header
- Spec §5 T5, §11.7
"""

import re
from typing import Any
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.deps import (
    ApiException,
    get_request_id,
)
from app.api.routers import (
    alerts,
    chat,
    feedback,
    health,
    history,
    kpi,
    metrics,
)
from app.core.config import Settings, get_settings
from app.core.errors import sanitize_db_error
from app.core.logging import request_id_ctx
from app.core.metrics import get_metrics_registry

_VALID_REQ_ID_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{4,64}$")


def _resolve_request_id(incoming_header: str | None) -> str:
    """Validate and sanitize incoming X-Request-ID header or generate a new unique id."""
    if incoming_header:
        cleaned = incoming_header.strip()
        if _VALID_REQ_ID_RE.match(cleaned):
            return cleaned
    return f"req-{uuid.uuid4().hex[:12]}"


def create_app(
    settings: Settings | None = None,
    dependency_overrides: dict | None = None,
) -> FastAPI:
    """Create, configure, and return the FastAPI application instance.

    Enforces TC-T5-09 production deployment safety check upfront.
    """
    app_settings = settings or get_settings()
    # TC-T5-09: Enforce safety check immediately
    app_settings.check_production_safety()

    app = FastAPI(
        title="Gỗ Minh Long AI Business Assistant API",
        version="2.0.0",
        description="Unified Enterprise AI Assistant for Financial & Operational Analytics",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Dependency overrides
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: app_settings
    if dependency_overrides:
        app.dependency_overrides.update(dependency_overrides)

    # 1. Request ID and observability middleware
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        req_id = _resolve_request_id(request.headers.get("x-request-id"))
        request.state.request_id = req_id
        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = req_id
            get_metrics_registry().record_request(request.url.path, response.status_code)
            return response
        finally:
            request_id_ctx.reset(token)

    # 2. Unified Error Handlers
    @app.exception_handler(ApiException)
    async def api_exception_handler(request: Request, exc: ApiException):
        req_id = get_request_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            headers={"x-request-id": req_id},
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": req_id,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        req_id = get_request_id(request)
        code = (
            "UNAUTHORIZED" if exc.status_code == 401 else
            "FORBIDDEN" if exc.status_code == 403 else
            "NOT_FOUND" if exc.status_code == 404 else
            "RATE_LIMIT_EXCEEDED" if exc.status_code == 429 else
            "HTTP_ERROR"
        )
        return JSONResponse(
            status_code=exc.status_code,
            headers={"x-request-id": req_id},
            content={
                "error": {
                    "code": code,
                    "message": str(exc.detail),
                    "request_id": req_id,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Review Focus #4: Traps 422 validation errors into unified error envelope."""
        req_id = get_request_id(request)
        errors = exc.errors()
        err_msgs = []
        for err in errors:
            loc = ".".join(str(l) for l in err.get("loc", []) if l != "body")
            msg = err.get("msg", "")
            err_msgs.append(f"{loc}: {msg}" if loc else msg)
        msg_text = "; ".join(err_msgs) if err_msgs else "Dữ liệu yêu cầu không hợp lệ."
        return JSONResponse(
            status_code=422,
            headers={"x-request-id": req_id},
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Dữ liệu yêu cầu không hợp lệ: {msg_text}",
                    "request_id": req_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = get_request_id(request)
        clean_msg = sanitize_db_error(str(exc))
        return JSONResponse(
            status_code=500,
            headers={"x-request-id": req_id},
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"Lỗi hệ thống nội bộ: {clean_msg}",
                    "request_id": req_id,
                }
            },
        )

    # 3. Mount Routers
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(kpi.router)
    app.include_router(alerts.router)
    app.include_router(feedback.router)
    app.include_router(history.router)
    app.include_router(metrics.router)

    return app


# Module-level default/lazy app instance
app = create_app()
