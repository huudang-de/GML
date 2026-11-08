"""FastAPI application factory and middleware wiring.

Specifications:
- Unified Error Envelope: {"error": {"code": str, "message": str, "request_id": str}}
- Spec §5 T5, §11.7
"""

import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.deps import ApiException, get_kpi_cache, get_rate_limiter, get_request_id
from app.api.routers import alerts, feedback, health, history, kpi, metrics
from app.core.config import Settings, get_settings
from app.core.errors import sanitize_db_error
from app.core.logging import request_id_ctx
from app.core.metrics import get_metrics_registry


def create_app(
    settings: Settings | None = None,
    dependency_overrides: dict | None = None,
) -> FastAPI:
    """Create and configure FastAPI application instance."""
    app_settings = settings or get_settings()

    app = FastAPI(
        title="Gỗ Minh Long AI Business Assistant API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Dependency overrides if specified
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings
    if dependency_overrides:
        app.dependency_overrides.update(dependency_overrides)

    # 1. Request ID and observability middleware
    @app.middleware("http")
    async def context_and_metrics_middleware(request: Request, call_next):
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = req_id
            get_metrics_registry().record_request(request.url.path, response.status_code)
            return response
        finally:
            request_id_ctx.reset(token)

    # 2. Unified error handlers
    @app.exception_handler(ApiException)
    async def api_exception_handler(request: Request, exc: ApiException):
        req_id = get_request_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": req_id,
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = get_request_id(request)
        code = "UNAUTHORIZED" if exc.status_code == 401 else (
            "FORBIDDEN" if exc.status_code == 403 else (
                "NOT_FOUND" if exc.status_code == 404 else (
                    "RATE_LIMIT_EXCEEDED" if exc.status_code == 429 else "HTTP_ERROR"
                )
            )
        )
        return JSONResponse(
            status_code=exc.status_code,
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
        req_id = get_request_id(request)
        err_msg = "; ".join([f"{'.'.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg', '')}" for err in exc.errors()])
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Dữ liệu yêu cầu không hợp lệ: {err_msg}",
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
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"Lỗi hệ thống nội bộ: {clean_msg}",
                    "request_id": req_id,
                }
            },
        )

    # 3. Mount routers
    app.include_router(health.router)
    app.include_router(kpi.router)
    app.include_router(alerts.router)
    app.include_router(feedback.router)
    app.include_router(history.router)
    app.include_router(metrics.router)

    return app
