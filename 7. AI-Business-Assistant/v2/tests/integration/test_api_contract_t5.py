"""Integration and contract test suite for FastAPI gateway and Phase 4 API endpoints (T5).

Specifications:
- TC-T5-01: Missing or invalid token returns 401 with unified envelope.
- TC-T5-02: Wrong role KPI access returns 403 and writes audit trail.
- TC-T5-03: Invalid schema returns 422 with unified envelope (no detail root key).
- TC-T5-04: Rate limit exceeded returns 429 with unified envelope.
- TC-T5-05: KPI endpoint returns exact G-01 value (236065233815.0) without LLM.
- TC-T5-06: /ready health probe returns 503 when PostgreSQL is unreachable.
- TC-T5-07 & M-14: Chat and blocked queries write clean audit trail without financial result values.
- M-13 & TC-T5-08: 100% of openapi paths exercised; openapi matches docs/openapi.json snapshot.
- TC-T5-09: Unsafe free-tier cloud LLM in production blocked during create_app().
- Review Focus #3: Audit log sanitization (financial numbers never in audit rows).
- Review Focus #4: RequestValidationError trapped in unified envelope with X-Request-ID.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.api.deps import reset_kpi_cache, reset_rate_limiter
from app.api.main import create_app
from app.core.config import Settings
from app.core.errors import UnsafeDeploymentError
from db.apply_db import get_app_engine


DOCS_OPENAPI_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "openapi.json"


@pytest.fixture(autouse=True)
def clean_singletons():
    """Reset rate limiter and cache singletons before each test."""
    reset_rate_limiter()
    reset_kpi_cache()
    yield
    reset_rate_limiter()
    reset_kpi_cache()


def test_tc_t5_01_missing_or_invalid_token_returns_401_unified_envelope():
    """TC-T5-01: Missing or invalid bearer token returns 401 with unified error envelope."""
    app = create_app()
    client = TestClient(app)

    # 1. Missing Authorization header
    res_missing = client.post("/v1/chat", json={"query": "Tổng dư nợ ngắn hạn"})
    assert res_missing.status_code == 401
    assert "x-request-id" in res_missing.headers
    req_id = res_missing.headers["x-request-id"]
    body_missing = res_missing.json()
    assert "error" in body_missing
    assert body_missing["error"]["code"] == "UNAUTHORIZED"
    assert body_missing["error"]["request_id"] == req_id
    assert "detail" not in body_missing

    # 2. Invalid bearer token
    res_invalid = client.post(
        "/v1/chat",
        headers={"Authorization": "Bearer totally-invalid-token"},
        json={"query": "Tổng dư nợ ngắn hạn"},
    )
    assert res_invalid.status_code == 401
    assert "x-request-id" in res_invalid.headers
    body_invalid = res_invalid.json()
    assert "error" in body_invalid
    assert body_invalid["error"]["code"] == "UNAUTHORIZED"
    assert body_invalid["error"]["request_id"] == res_invalid.headers["x-request-id"]


def test_tc_t5_02_wrong_role_kpi_returns_403_and_audits():
    """TC-T5-02: quan_ly_kho calling /v1/kpi/du_no_ngan_han returns 403 and writes an audit log."""
    app = create_app()
    client = TestClient(app)

    custom_req_id = "req-audit-test-403"
    res = client.get(
        "/v1/kpi/du_no_ngan_han",
        headers={
            "Authorization": "Bearer gml-dev-token-kho",
            "X-Request-ID": custom_req_id,
        },
    )
    assert res.status_code == 403
    body = res.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["request_id"] == custom_req_id

    # Verify audit log row was written for this request_id
    engine = get_app_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT user_id, role, query, request_id FROM app.audit_log WHERE request_id = :req_id"),
            {"req_id": custom_req_id},
        ).fetchone()

    assert row is not None
    assert row.user_id == "usr_kho"
    assert row.role == "quan_ly_kho"
    assert "du_no_ngan_han" in row.query


def test_tc_t5_03_and_review_focus_4_invalid_schema_returns_422_unified_envelope():
    """TC-T5-03 & Review Focus #4: Invalid schema returns 422 with unified envelope, no raw detail."""
    app = create_app()
    client = TestClient(app)

    req_id = "req-val-fail-001"
    # Empty JSON body violates ChatRequest schema (missing required query)
    res = client.post(
        "/v1/chat",
        headers={
            "Authorization": "Bearer gml-dev-token-ceo",
            "X-Request-ID": req_id,
        },
        json={},
    )
    assert res.status_code == 422
    assert res.headers["x-request-id"] == req_id

    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["request_id"] == req_id
    assert "detail" not in body  # Must NOT expose raw FastAPI 'detail'


def test_tc_t5_04_rate_limit_exceeded_returns_429():
    """TC-T5-04: Exceeding rate_limit_per_minute returns 429 in unified envelope."""
    settings = Settings(rate_limit_per_minute=2)
    app = create_app(settings=settings)
    client = TestClient(app)

    headers = {"Authorization": "Bearer gml-dev-token-ceo"}

    # Requests 1 and 2 succeed
    res1 = client.get("/v1/history", headers=headers)
    assert res1.status_code == 200

    res2 = client.get("/v1/history", headers=headers)
    assert res2.status_code == 200

    # Request 3 exceeds limit -> 429
    res3 = client.get("/v1/history", headers=headers)
    assert res3.status_code == 429
    body3 = res3.json()
    assert body3["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert body3["error"]["request_id"] == res3.headers["x-request-id"]


def test_tc_t5_05_kpi_endpoint_without_llm_returns_exact_g01():
    """TC-T5-05: GET /v1/kpi/du_no_ngan_han with blank google_api_key returns exact 236065233815.0."""
    no_llm_settings = Settings(google_api_key="")
    app = create_app(settings=no_llm_settings)
    client = TestClient(app)

    res = client.get(
        "/v1/kpi/du_no_ngan_han",
        headers={"Authorization": "Bearer gml-dev-token-ceo"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["kpi_key"] == "du_no_ngan_han"
    assert data["value"] == 236065233815.0
    assert "ai_v_no_vay" in data["sql_executed"]


def test_tc_t5_06_ready_reflects_db_down_503():
    """TC-T5-06: /ready health probe returns 503 with db: down when PostgreSQL is unreachable."""
    bad_settings = Settings(
        postgres_uri_app="postgresql+psycopg2://invalid:secret@localhost:9999/down_db",
        postgres_uri_ro="postgresql+psycopg2://invalid:secret@localhost:9999/down_db",
    )
    app = create_app(settings=bad_settings)
    client = TestClient(app)

    res = client.get("/ready")
    assert res.status_code == 503
    data = res.json()
    assert data["db"] == "down"
    assert data["status"] == "not_ready"
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_tc_t5_07_and_m14_chat_and_blocked_requests_write_clean_audit_log():
    """TC-T5-07, M-14 & Review Focus #3: Chat and blocked queries write audit log with zero financial values."""
    app = create_app()
    client = TestClient(app)

    req_valid = "req-chat-valid-001"
    req_blocked = "req-chat-blocked-002"

    # 1. Valid chat query
    res_valid = client.post(
        "/v1/chat",
        headers={"Authorization": "Bearer gml-dev-token-ceo", "X-Request-ID": req_valid},
        json={"query": "Dư nợ ngắn hạn hiện tại là bao nhiêu?"},
    )
    assert res_valid.status_code == 200
    valid_data = res_valid.json()
    assert valid_data["session_id"] is not None

    # 2. Blocked DDL/DML query
    res_blocked = client.post(
        "/v1/chat",
        headers={"Authorization": "Bearer gml-dev-token-ceo", "X-Request-ID": req_blocked},
        json={"query": "Xoá bảng nợ vay"},
    )
    assert res_blocked.status_code == 200
    blocked_data = res_blocked.json()
    assert blocked_data["intent"] == "blocked"

    # 3. Assert M-14: Audit rows exist for both request IDs
    engine = get_app_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT user_id, role, query, sql_executed, views_accessed, request_id, execution_time_ms
                FROM app.audit_log
                WHERE request_id IN (:r1, :r2)
            """),
            {"r1": req_valid, "r2": req_blocked},
        ).fetchall()

    found_reqs = {r.request_id: r for r in rows}
    assert req_valid in found_reqs, f"Request {req_valid} must be audited (M-14)"
    assert req_blocked in found_reqs, f"Request {req_blocked} must be audited (M-14)"

    # 4. Review Focus #3: Financial value (236065233815) must NEVER appear anywhere in audit rows
    for r in rows:
        row_str = f"{r.user_id} {r.role} {r.query} {r.sql_executed} {r.views_accessed} {r.request_id}"
        assert "236065233815" not in row_str, "Financial value leaked into audit log row!"


def test_m13_100_percent_endpoint_contract_coverage_and_tc_t5_08_openapi_snapshot():
    """M-13 & TC-T5-08: 100% of endpoints in openapi paths are exercised and snapshot matches."""
    app = create_app()
    client = TestClient(app)

    # 1. Verify OpenAPI snapshot (TC-T5-08)
    current_openapi = app.openapi()
    assert DOCS_OPENAPI_PATH.exists(), f"OpenAPI snapshot file {DOCS_OPENAPI_PATH} must exist"
    snapshot_openapi = json.loads(DOCS_OPENAPI_PATH.read_text(encoding="utf-8"))

    # Compare paths and info
    assert current_openapi["paths"] == snapshot_openapi["paths"], "OpenAPI paths mismatch snapshot"

    # 2. Exercise 100% of registered endpoint paths (M-13)
    registered_paths = set(current_openapi["paths"].keys())
    expected_paths = {
        "/v1/chat",
        "/v1/kpi/{key}",
        "/v1/alerts",
        "/v1/alerts/{alert_id}/ack",
        "/v1/feedback",
        "/v1/history",
        "/health",
        "/ready",
        "/metrics",
    }
    assert expected_paths.issubset(registered_paths), f"Missing paths: {expected_paths - registered_paths}"

    auth_ceo = {"Authorization": "Bearer gml-dev-token-ceo"}

    # Exercise every path:
    # 1. /health
    assert client.get("/health").status_code == 200

    # 2. /ready
    assert client.get("/ready").status_code in (200, 503)

    # 3. /metrics
    assert client.get("/metrics", headers=auth_ceo).status_code == 200

    # 4. /v1/chat
    chat_res = client.post("/v1/chat", headers=auth_ceo, json={"query": "Tỷ lệ sử dụng hạn mức?"})
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    sess_id = chat_data["session_id"]

    # 5. /v1/kpi/{key}
    assert client.get("/v1/kpi/du_no_ngan_han", headers=auth_ceo).status_code == 200

    # 6. /v1/alerts (GET)
    alerts_res = client.get("/v1/alerts", headers=auth_ceo)
    assert alerts_res.status_code == 200

    # 7. /v1/alerts/{alert_id}/ack (POST) - use 999999 non-existent or 0 to test endpoint execution
    ack_res = client.post("/v1/alerts/999999/ack", headers=auth_ceo)
    assert ack_res.status_code in (200, 404)

    # 8. /v1/feedback (POST)
    fb_res = client.post(
        "/v1/feedback",
        headers=auth_ceo,
        json={"request_id": "req-fb-contract", "rating": "up", "comment": "Good answer"},
    )
    assert fb_res.status_code == 200

    # 9. /v1/history (GET and DELETE)
    assert client.get(f"/v1/history?session_id={sess_id}", headers=auth_ceo).status_code == 200
    assert client.delete(f"/v1/history?session_id={sess_id}", headers=auth_ceo).status_code == 200


def test_tc_t5_09_create_app_blocks_unsafe_production_config():
    """TC-T5-09: Calling create_app with production free-tier cloud LLM raises UnsafeDeploymentError."""
    with pytest.raises(UnsafeDeploymentError):
        create_app(Settings(app_env="production", llm_provider="gemini", llm_tier="free"))
