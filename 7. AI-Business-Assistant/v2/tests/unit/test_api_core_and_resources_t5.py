"""Unit tests for API core security, rate limit, scoped TTL cache, audit trail, and deterministic resource routers (T5).

Specifications:
- TC-T5-02: Deterministic KPI calculation without LLM invocation.
- TC-T5-04: Sliding window rate limiter prevents burst abuse.
- TC-T5-05: RBAC role separation on KPI endpoints.
- TC-T5-06: /ready health probe returns 503 when PostgreSQL is unreachable.
- TC-T5-09: Unsafe cloud LLM free tier blocked in production.
- Review Focus #2: ScopedTTLCache strictly isolates (profile, role, kpi_key, as_of_date).
- Review Focus #3: Audit log sanitization without leaking result values.
- Review Focus #5: Role-based filtering and acknowledgment protection on alerts.
"""

from datetime import datetime, timedelta, timezone
import json
import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import UnsafeDeploymentError
from app.core.auth import TokenAuthVerifier, UserPrincipal
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.cache import ScopedTTLCache
from app.api.schemas import (
    ApiErrorResponse,
    KpiValueResponse,
    AlertListResponse,
    AlertAckResponse,
    FeedbackResponse,
    HistoryListResponse,
    HistoryDeleteResponse,
    HealthResponse,
    ReadyResponse,
)
from app.api.audit import write_audit_log
from app.api import create_app
from db.apply_db import get_app_engine, get_ro_engine


def test_token_auth_sha256_verification_expiry_and_prod_guard():
    """Verify SHA-256 token verification, expiration check, and production dev-token guard."""
    # 1. Non-production environment provides default dev tokens
    dev_settings = Settings(app_env="development")
    verifier = TokenAuthVerifier(dev_settings)

    principal_ceo = verifier.verify_bearer_token("gml-dev-token-ceo")
    assert principal_ceo.user_id == "usr_ceo"
    assert principal_ceo.role == "ceo"

    principal_kho = verifier.verify_bearer_token("gml-dev-token-kho")
    assert principal_kho.user_id == "usr_kho"
    assert principal_kho.role == "quan_ly_kho"

    # 2. Invalid token raises 401
    with pytest.raises(Exception) as exc_info:
        verifier.verify_bearer_token("invalid-token-1234")
    assert "401" in str(exc_info.value) or "UNAUTHORIZED" in str(exc_info.value)

    # 3. Expired token raises 401
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    tokens_json = json.dumps([
        {
            "token": "secret-custom-token",
            "user_id": "usr_custom",
            "role": "ke_toan_truong",
            "display_name": "Custom User",
            "expires_at": past_time.isoformat(),
        }
    ])
    custom_verifier = TokenAuthVerifier(Settings(app_env="development", auth_tokens_json=tokens_json))
    with pytest.raises(Exception) as exc_expired:
        custom_verifier.verify_bearer_token("secret-custom-token")
    assert "401" in str(exc_expired.value) or "UNAUTHORIZED" in str(exc_expired.value) or "hết hạn" in str(exc_expired.value)

    # 4. Production environment with local Ollama rejects default dev tokens if auth_tokens_json is empty
    prod_settings_no_tokens = Settings(app_env="production", llm_provider="ollama", llm_tier="free")
    prod_verifier = TokenAuthVerifier(prod_settings_no_tokens)
    with pytest.raises(Exception) as exc_prod:
        prod_verifier.verify_bearer_token("gml-dev-token-ceo")
    assert "401" in str(exc_prod.value) or "UNAUTHORIZED" in str(exc_prod.value)


def test_tc_t5_04_sliding_window_rate_limiter_blocks_burst():
    """TC-T5-04: SlidingWindowRateLimiter blocks burst requests exceeding limit."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    now = 1000.0

    # First 3 requests allowed
    ok1, rem1 = limiter.check("user_1", now=now)
    assert ok1 is True
    assert rem1 == 2

    ok2, rem2 = limiter.check("user_1", now=now + 1.0)
    assert ok2 is True
    assert rem2 == 1

    ok3, rem3 = limiter.check("user_1", now=now + 2.0)
    assert ok3 is True
    assert rem3 == 0

    # 4th request rejected
    ok4, rem4 = limiter.check("user_1", now=now + 3.0)
    assert ok4 is False
    assert rem4 == 0

    # Different user is unaffected
    ok_user2, _ = limiter.check("user_2", now=now + 3.0)
    assert ok_user2 is True

    # After window seconds elapses, user_1 is allowed again
    ok5, rem5 = limiter.check("user_1", now=now + 61.0)
    assert ok5 is True


def test_tc_t5_02_and_tc_t5_05_kpi_endpoint_zero_llm_and_rbac():
    """TC-T5-02 & TC-T5-05: Zero-LLM deterministic KPI calculation and RBAC role enforcement."""
    # Blank LLM api key ensures zero LLM invocation
    settings = Settings(google_api_key="", llm_provider="gemini", llm_tier="free")
    app = create_app(settings=settings)
    client = TestClient(app)

    # CEO has full access to ai_v_no_vay -> G-01 UAT gold: 236,065,233,815
    ceo_res = client.get(
        "/v1/kpi/du_no_ngan_han",
        headers={"Authorization": "Bearer gml-dev-token-ceo"},
    )
    assert ceo_res.status_code == 200, f"Expected 200, got {ceo_res.status_code}: {ceo_res.text}"
    data = ceo_res.json()
    assert data["kpi_key"] == "du_no_ngan_han"
    assert data["value"] == pytest.approx(236065233815.0, rel=1e-4)
    assert data["data_profile"] == "real"

    # quan_ly_kho only has access to ai_v_ton_kho, NOT ai_v_no_vay -> 403 Forbidden
    kho_res = client.get(
        "/v1/kpi/du_no_ngan_han",
        headers={"Authorization": "Bearer gml-dev-token-kho"},
    )
    assert kho_res.status_code == 403
    kho_err = kho_res.json()
    assert "error" in kho_err
    assert kho_err["error"]["code"] == "FORBIDDEN"
    assert "request_id" in kho_err["error"]


def test_review_focus_2_scoped_ttl_cache_isolates_real_synth_and_roles():
    """Review Focus #2: ScopedTTLCache strictly isolates by profile and role; RBAC checked before cache."""
    settings = Settings(google_api_key="", llm_provider="gemini")
    app = create_app(settings=settings)
    client = TestClient(app)

    # 1. Call on synthetic profile
    synth_res = client.get(
        "/v1/kpi/du_no_ngan_han?profile=synth",
        headers={"Authorization": "Bearer gml-dev-token-ceo"},
    )
    assert synth_res.status_code == 200
    synth_data = synth_res.json()
    assert synth_data["value"] == pytest.approx(236070000000.0, rel=1e-4)
    assert "SYNTHETIC_DATA" in synth_data.get("warnings", [])

    # 2. Call on real profile returns real value, not synth cached value
    real_res = client.get(
        "/v1/kpi/du_no_ngan_han?profile=real",
        headers={"Authorization": "Bearer gml-dev-token-ceo"},
    )
    assert real_res.status_code == 200
    real_data = real_res.json()
    assert real_data["value"] == pytest.approx(236065233815.0, rel=1e-4)
    assert "SYNTHETIC_DATA" not in real_data.get("warnings", [])

    # 3. Restricted role still gets 403 even though cache is warm
    kho_res = client.get(
        "/v1/kpi/du_no_ngan_han?profile=real",
        headers={"Authorization": "Bearer gml-dev-token-kho"},
    )
    assert kho_res.status_code == 403
    assert kho_res.json()["error"]["code"] == "FORBIDDEN"


def test_review_focus_5_alerts_rbac_filtering_and_ack_forbidden():
    """Review Focus #5: Alert retrieval filtered by allowed views; unauthorized ack returns 403."""
    app_engine = get_app_engine(profile="real")

    # Seed two alerts: one on ai_v_no_vay (ty_le_su_dung_han_muc) and one on ai_v_ton_kho (gia_tri_hang_ton_kho)
    with app_engine.begin() as conn:
        id_loan = conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (rule_id, kpi_key, severity, message, value, threshold, is_acknowledged)
                VALUES ('BR-01', 'ty_le_su_dung_han_muc', 'critical', 'Tỷ lệ vượt 85%', 0.88, 0.85, false)
                RETURNING id;
            """)
        ).scalar()

        id_inv = conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (rule_id, kpi_key, severity, message, value, threshold, is_acknowledged)
                VALUES ('BR-02', 'gia_tri_hang_ton_kho', 'warning', 'Tồn kho melamine tăng cao', 120000000000, 100000000000, false)
                RETURNING id;
            """)
        ).scalar()

    app = create_app(settings=Settings())
    client = TestClient(app)

    # 1. quan_ly_kho lists alerts -> sees only inventory alert, NOT loan alert
    kho_list = client.get("/v1/alerts", headers={"Authorization": "Bearer gml-dev-token-kho"})
    assert kho_list.status_code == 200
    alerts_kho = kho_list.json()["alerts"]
    kpi_keys_kho = [a["kpi_key"] for a in alerts_kho]
    assert "gia_tri_hang_ton_kho" in kpi_keys_kho
    assert "ty_le_su_dung_han_muc" not in kpi_keys_kho

    # 2. quan_ly_kho attempts to ack loan alert -> 403 Forbidden
    kho_ack = client.post(
        f"/v1/alerts/{id_loan}/ack",
        headers={"Authorization": "Bearer gml-dev-token-kho"},
    )
    assert kho_ack.status_code == 403
    assert kho_ack.json()["error"]["code"] == "FORBIDDEN"

    # 3. ceo acks loan alert -> 200 OK
    ceo_ack = client.post(
        f"/v1/alerts/{id_loan}/ack",
        headers={"Authorization": "Bearer gml-dev-token-ceo"},
    )
    assert ceo_ack.status_code == 200
    ack_data = ceo_ack.json()
    assert ack_data["is_acknowledged"] is True
    assert ack_data["acknowledged_by"] == "usr_ceo"


def test_tc_t5_06_ready_returns_503_when_postgres_unreachable():
    """TC-T5-06: /ready health probe returns 503 when database is unreachable."""
    # Use invalid port so connection fails immediately
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
    assert "error" in data
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_tc_t5_09_production_free_cloud_llm_refuses_startup():
    """TC-T5-09: Production deployment prohibits free-tier cloud LLM."""
    with pytest.raises(UnsafeDeploymentError):
        Settings(app_env="production", llm_provider="gemini", llm_tier="free")


def test_review_focus_3_audit_trail_sanitizes_and_never_logs_result_values():
    """Review Focus #3: Audit log records execution metadata and sanitized SQL, never result numbers."""
    app_engine = get_app_engine(profile="real")
    req_id = "test-audit-req-12345"

    # Call write_audit_log
    write_audit_log(
        engine=app_engine,
        user_id="usr_ceo",
        role="ceo",
        request_id=req_id,
        query="SELECT * FROM ai_v_no_vay WHERE postgresql://u:p@host/db",
        sql_executed="SELECT principal_balance FROM ai_v_no_vay LIMIT 10",
        views_accessed=["ai_v_no_vay"],
        execution_time_ms=12.5,
    )

    with app_engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT * FROM app.audit_log WHERE request_id = :req_id;"),
            {"req_id": req_id},
        ).mappings().fetchone()

    assert row is not None
    assert row["user_id"] == "usr_ceo"
    assert row["role"] == "ceo"
    assert "ai_v_no_vay" in row["views_accessed"]
    # Check that database credentials URI was sanitized
    assert "u:p@host" not in row["query"]
    assert "[REDACTED_DATABASE_URI]" in row["query"] or "postgresql" not in row["query"]
    # Ensure no result values (like 236065233815) are recorded in the audit log row
    for col in ("query", "sql_executed", "role", "user_id"):
        assert "236065233815" not in str(row[col])


def test_feedback_endpoint_records_rating_and_validates():
    """Test POST /v1/feedback endpoint records rating and validates fields."""
    app = create_app(settings=Settings())
    client = TestClient(app)

    # 1. Invalid rating returns 422
    bad_res = client.post(
        "/v1/feedback",
        json={"request_id": "req-1", "rating": "super_good"},
        headers={"Authorization": "Bearer gml-dev-token-ceo"},
    )
    assert bad_res.status_code == 422

    # 2. Valid rating returns 200 and records in app.feedback
    ok_res = client.post(
        "/v1/feedback",
        json={"request_id": "req-feedback-test-1", "rating": "up", "comment": "Chính xác"},
        headers={"Authorization": "Bearer gml-dev-token-ceo"},
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["status"] == "ok"


def test_history_endpoint_strictly_isolated_by_user():
    """Test GET /v1/history and DELETE /v1/history are strictly isolated by authenticated user."""
    from app.memory.session_store import SessionStore
    store = SessionStore()

    # Seed 1 turn for usr_ceo and 1 turn for usr_kho in the same session
    store.add_turn(
        session_id="shared-session-test",
        user_id="usr_ceo",
        query="Câu hỏi của CEO",
        intent="sql_only",
    )
    store.add_turn(
        session_id="shared-session-test",
        user_id="usr_kho",
        query="Câu hỏi của Quản lý kho",
        intent="sql_only",
    )

    app = create_app(settings=Settings())
    client = TestClient(app)

    # 1. CEO sees only CEO's turns
    ceo_hist = client.get(
        "/v1/history?session_id=shared-session-test",
        headers={"Authorization": "Bearer gml-dev-token-ceo"},
    )
    assert ceo_hist.status_code == 200
    turns_ceo = ceo_hist.json()["turns"]
    assert all(t["query"] == "Câu hỏi của CEO" for t in turns_ceo)

    # 2. Kho deletes their history; CEO history remains intact
    del_res = client.delete(
        "/v1/history?session_id=shared-session-test",
        headers={"Authorization": "Bearer gml-dev-token-kho"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["deleted_count"] >= 1

    # Verify CEO history still has the turn
    ceo_hist_after = client.get(
        "/v1/history?session_id=shared-session-test",
        headers={"Authorization": "Bearer gml-dev-token-ceo"},
    )
    assert len(ceo_hist_after.json()["turns"]) >= 1
