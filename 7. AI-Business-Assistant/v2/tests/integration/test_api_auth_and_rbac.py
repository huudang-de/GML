"""Integration tests for stateful DB session auth, /v1/auth/* endpoints, and profile/password gates (Task 2).

Specifications:
- Design §5.3, §5.4, §5.5
- Plan Task 2
"""

from datetime import datetime
import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.api import deps
from app.api.deps import reset_kpi_cache, reset_rate_limiter
from app.api.main import create_app
from app.core.auth import AuthenticationError, TokenAuthVerifier
from app.core.config import Settings, get_settings
from app.services.iam_service import create_session, create_user
from db.apply_db import get_admin_engine, get_app_engine, get_iam_engine


TEST_USERNAMES = (
    "t2_ceo_user",
    "t2_temp_user",
    "t2_ktt_real_only",
    "t2_kho_real",
    "t2_locked_user",
    "t2_disabled_user",
)


@pytest.fixture(autouse=True)
def clean_singletons_and_test_users(monkeypatch: pytest.MonkeyPatch):
    """Isolate singletons, offline mock LLM, and clean up Task 2 IAM test rows."""
    monkeypatch.setenv("GOOGLE_API_KEY", "mock_offline")
    get_settings.cache_clear()
    reset_rate_limiter()
    reset_kpi_cache()
    reset_login_fn = getattr(deps, "reset_login_rate_limiter", None)
    if callable(reset_login_fn):
        reset_login_fn()

    def _clean():
        try:
            admin_eng = get_admin_engine(profile="real")
            with admin_eng.begin() as conn:
                conn.execute(
                    sa.text(
                        "DELETE FROM iam.user_session WHERE user_id IN ("
                        "  SELECT user_id FROM iam.app_user WHERE lower(username) = ANY(:names)"
                        ")"
                    ),
                    {"names": list(TEST_USERNAMES)},
                )
                conn.execute(
                    sa.text(
                        "DELETE FROM iam.auth_event WHERE lower(coalesce(username_attempted, '')) = ANY(:names) "
                        "OR user_id IN (SELECT user_id FROM iam.app_user WHERE lower(username) = ANY(:names))"
                    ),
                    {"names": list(TEST_USERNAMES)},
                )
                conn.execute(
                    sa.text("DELETE FROM iam.app_user WHERE lower(username) = ANY(:names)"),
                    {"names": list(TEST_USERNAMES)},
                )
        except Exception:
            pass

    _clean()
    yield
    _clean()
    reset_rate_limiter()
    reset_kpi_cache()
    if callable(reset_login_fn):
        reset_login_fn()
    get_settings.cache_clear()


@pytest.fixture
def iam_eng():
    return get_iam_engine()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def iam_user_factory(iam_eng):
    def _make(
        *,
        username: str,
        display_name: str,
        role: str,
        password: str = "StrongPass@2026",
        allowed_profiles: list[str] | None = None,
        must_change_password: bool = False,
        email: str | None = None,
    ):
        user, plain_pw = create_user(
            iam_eng,
            username=username,
            display_name=display_name,
            role=role,
            allowed_profiles=allowed_profiles,
            email=email,
            password=password,
            must_change_password=must_change_password,
        )
        return user, plain_pw

    return _make


def test_login_logout_me_and_immediate_revocation(client, iam_user_factory):
    user, pw = iam_user_factory(
        username="t2_ceo_user",
        display_name="Nguyễn Văn T2",
        role="ceo",
        email="t2.ceo@gominhlong.local",
        must_change_password=False,
    )

    login_req_id = f"req-t2-login-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/v1/auth/login",
        json={"username": "T2_CEO_USER", "password": pw},
        headers={"X-Request-ID": login_req_id},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_at"]
    assert body["user"]["user_id"] == user["user_id"]
    assert body["user"]["username"] == "t2_ceo_user"
    assert body["user"]["display_name"] == "Nguyễn Văn T2"
    assert body["user"]["email"] == "t2.ceo@gominhlong.local"
    assert body["user"]["role"] == "ceo"
    assert body["user"]["allowed_profiles"] == ["real", "synth"]
    assert body["user"]["must_change_password"] is False
    assert "password_hash" not in body["user"]

    token = body["access_token"]
    hdr = {"Authorization": f"Bearer {token}"}

    # /v1/auth/me works with DB session token
    me_res = client.get("/v1/auth/me", headers=hdr)
    assert me_res.status_code == 200, me_res.text
    me_body = me_res.json()
    assert me_body["user_id"] == user["user_id"]
    assert me_body["username"] == "t2_ceo_user"
    assert me_body["role"] == "ceo"

    # Audit log written for login without leaking password or raw token
    app_eng = get_app_engine(profile="real")
    with app_eng.connect() as conn:
        audit_row = conn.execute(
            sa.text("SELECT user_id, role, query FROM app.audit_log WHERE request_id = :rid"),
            {"rid": login_req_id},
        ).fetchone()
    assert audit_row is not None
    assert audit_row.user_id == user["user_id"]
    assert pw not in (audit_row.query or "")
    assert token not in (audit_row.query or "")

    # Logout revokes session immediately
    logout_req_id = f"req-t2-logout-{uuid.uuid4().hex[:8]}"
    logout_res = client.post("/v1/auth/logout", headers={**hdr, "X-Request-ID": logout_req_id})
    assert logout_res.status_code == 200, logout_res.text
    assert logout_res.json() == {"status": "ok"}

    # Immediate revocation: /v1/auth/me and business API return 401
    me_after = client.get("/v1/auth/me", headers=hdr)
    assert me_after.status_code == 401
    assert me_after.json()["error"]["code"] == "UNAUTHORIZED"

    ov_after = client.get("/v1/overview", headers=hdr)
    assert ov_after.status_code == 401


def test_login_invalid_credentials_and_account_lockout_423(client, iam_user_factory):
    user, pw = iam_user_factory(
        username="t2_locked_user",
        display_name="Locked T2",
        role="ke_toan_truong",
        password="LockStrong@2026",
    )

    # Non-existent user -> 401 INVALID_CREDENTIALS
    r_missing = client.post(
        "/v1/auth/login",
        json={"username": "no_such_user_t2", "password": "SomePassword99!"},
    )
    assert r_missing.status_code == 401
    assert r_missing.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # Wrong password 5 times -> 401 INVALID_CREDENTIALS, then 6th (even with right password) -> 423 ACCOUNT_LOCKED
    for _ in range(5):
        r_bad = client.post(
            "/v1/auth/login",
            json={"username": "t2_locked_user", "password": "WrongPassword99!"},
        )
        assert r_bad.status_code == 401
        assert r_bad.json()["error"]["code"] == "INVALID_CREDENTIALS"

    r_locked = client.post(
        "/v1/auth/login",
        json={"username": "t2_locked_user", "password": pw},
    )
    assert r_locked.status_code == 423
    err = r_locked.json()["error"]
    assert err["code"] == "ACCOUNT_LOCKED"
    # Verify ISO timestamp is included in error message
    assert "T" in err["message"] and ("+" in err["message"] or "Z" in err["message"])

    # Disabled user returns 401 INVALID_CREDENTIALS
    dis_user, dis_pw = iam_user_factory(
        username="t2_disabled_user",
        display_name="Disabled T2",
        role="quan_ly_kho",
        password="DisabledStrong@2026",
    )
    with get_admin_engine(profile="real").begin() as conn:
        conn.execute(
            sa.text("UPDATE iam.app_user SET is_active = FALSE WHERE user_id = :uid"),
            {"uid": dis_user["user_id"]},
        )
    r_dis = client.post(
        "/v1/auth/login",
        json={"username": "t2_disabled_user", "password": dis_pw},
    )
    assert r_dis.status_code == 401
    assert r_dis.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_must_change_password_blocks_business_routes_until_changed(client, iam_eng, iam_user_factory):
    temp_user, temp_pw = iam_user_factory(
        username="t2_temp_user",
        display_name="Temp Password User",
        role="ceo",
        password="TempPass@2026",
        must_change_password=True,
    )

    # Create a second earlier session to ensure change-password keeps current & revokes others
    other_tok, _ = create_session(iam_eng, user_id=temp_user["user_id"])

    login_res = client.post(
        "/v1/auth/login",
        json={"username": "t2_temp_user", "password": temp_pw},
    )
    assert login_res.status_code == 200
    assert login_res.json()["user"]["must_change_password"] is True
    token = login_res.json()["access_token"]
    hdr = {"Authorization": f"Bearer {token}"}

    # /v1/auth/me is allowed while must_change_password is True
    assert client.get("/v1/auth/me", headers=hdr).status_code == 200

    # Business routes are blocked with 403 PASSWORD_CHANGE_REQUIRED
    for method, url, kwargs in (
        ("GET", "/v1/overview", {}),
        ("GET", "/v1/kpi/du_no_ngan_han", {}),
        ("POST", "/v1/chat", {"json": {"query": "Dư nợ ngắn hạn?"}}),
    ):
        res = client.request(method, url, headers=hdr, **kwargs)
        assert res.status_code == 403, f"Expected 403 for {url}, got {res.status_code}: {res.text}"
        assert res.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    # Wrong current_password -> 401 INVALID_CREDENTIALS
    bad_cur = client.post(
        "/v1/auth/change-password",
        headers=hdr,
        json={"current_password": "WrongCurrent99!", "new_password": "BrandNewPass@2026"},
    )
    assert bad_cur.status_code == 401
    assert bad_cur.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # Policy violation -> 422 PASSWORD_POLICY_ERROR
    weak_new = client.post(
        "/v1/auth/change-password",
        headers=hdr,
        json={"current_password": temp_pw, "new_password": "minhlong123"},
    )
    assert weak_new.status_code == 422
    assert weak_new.json()["error"]["code"] == "PASSWORD_POLICY_ERROR"

    # Valid change-password -> 200 and clears gate immediately
    new_pw = "BrandNewPass@2026"
    cp_req_id = f"req-t2-cp-{uuid.uuid4().hex[:8]}"
    ok_cp = client.post(
        "/v1/auth/change-password",
        headers={**hdr, "X-Request-ID": cp_req_id},
        json={"current_password": temp_pw, "new_password": new_pw},
    )
    assert ok_cp.status_code == 200, ok_cp.text
    assert ok_cp.json()["status"] == "ok"

    # Audit log must not leak passwords
    app_eng = get_app_engine(profile="real")
    with app_eng.connect() as conn:
        cp_audit = conn.execute(
            sa.text("SELECT query FROM app.audit_log WHERE request_id = :rid"),
            {"rid": cp_req_id},
        ).fetchone()
    assert cp_audit is not None
    assert temp_pw not in (cp_audit.query or "")
    assert new_pw not in (cp_audit.query or "")

    # Current session stays active and can now access /v1/overview; old session is revoked
    me_after = client.get("/v1/auth/me", headers=hdr)
    assert me_after.status_code == 200
    assert me_after.json()["must_change_password"] is False

    ov_after = client.get("/v1/overview", headers=hdr)
    assert ov_after.status_code == 200

    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {other_tok}"}).status_code == 401


def test_profile_forbidden_on_get_and_chat_when_user_lacks_synth(client, iam_user_factory):
    _, pw = iam_user_factory(
        username="t2_ktt_real_only",
        display_name="KTT Real Only",
        role="ke_toan_truong",
        allowed_profiles=["real"],
        password="KttRealStrong@2026",
    )
    login_res = client.post(
        "/v1/auth/login",
        json={"username": "t2_ktt_real_only", "password": pw},
    )
    assert login_res.status_code == 200
    hdr = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # Allowed real profile works
    assert client.get("/v1/overview?profile=real", headers=hdr).status_code == 200
    assert client.post("/v1/chat", json={"query": "Dư nợ?", "data_profile": "real"}, headers=hdr).status_code == 200

    # Forbidden synth profile blocked with 403 PROFILE_FORBIDDEN across GET/POST/DELETE routes
    for method, url, kwargs in (
        ("GET", "/v1/overview?profile=synth", {}),
        ("GET", "/v1/kpi/du_no_ngan_han?profile=synth", {}),
        ("GET", "/v1/alerts?profile=synth", {}),
        ("GET", "/v1/actions?profile=synth", {}),
        ("GET", "/v1/pins?profile=synth", {}),
        ("GET", "/v1/history?profile=synth", {}),
        ("DELETE", "/v1/history?profile=synth", {}),
        ("POST", "/v1/feedback?profile=synth", {"json": {"request_id": "req-t2-fb", "rating": "up", "comment": ""}}),
        ("POST", "/v1/chat", {"json": {"query": "Dư nợ?", "data_profile": "synth"}}),
    ):
        res = client.request(method, url, headers=hdr, **kwargs)
        assert res.status_code == 403, f"Expected 403 for {url}, got {res.status_code}: {res.text}"
        assert res.json()["error"]["code"] == "PROFILE_FORBIDDEN"


def test_kho_real_session_cannot_access_finance_kpi_or_admin(client, iam_user_factory):
    _, pw = iam_user_factory(
        username="t2_kho_real",
        display_name="Kho Real",
        role="quan_ly_kho",
        allowed_profiles=["real"],
        password="KhoRealStrong@2026",
    )
    login_res = client.post(
        "/v1/auth/login",
        json={"username": "t2_kho_real", "password": pw},
    )
    assert login_res.status_code == 200
    hdr = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # Allowed inventory KPI on real profile -> 200
    inv_res = client.get("/v1/kpi/gia_tri_hang_ton_kho?profile=real", headers=hdr)
    assert inv_res.status_code == 200

    # Finance KPI -> 403 FORBIDDEN
    fin_res = client.get("/v1/kpi/du_no_ngan_han?profile=real", headers=hdr)
    assert fin_res.status_code == 403
    assert fin_res.json()["error"]["code"] == "FORBIDDEN"

    # Pin finance KPI -> 403 FORBIDDEN
    pin_res = client.post("/v1/pins?profile=real", json={"kpi_key": "du_no_ngan_han"}, headers=hdr)
    assert pin_res.status_code == 403
    assert pin_res.json()["error"]["code"] == "FORBIDDEN"

    # Admin route -> 403 once /v1/admin is mounted (or 404 before Task 3 mounts it)
    admin_res = client.get("/v1/admin/users", headers=hdr)
    if "/v1/admin/users" in client.app.openapi()["paths"]:
        assert admin_res.status_code == 403
        assert admin_res.json()["error"]["code"] == "FORBIDDEN"
    else:
        assert admin_res.status_code == 404


def test_login_rate_limit_10_per_minute_per_ip(client):
    for i in range(10):
        res = client.post(
            "/v1/auth/login",
            json={"username": "unknown_rate_test", "password": "BadPassword99!"},
        )
        assert res.status_code == 401, f"Attempt {i + 1} expected 401, got {res.status_code}"

    blocked = client.post(
        "/v1/auth/login",
        json={"username": "unknown_rate_test", "password": "BadPassword99!"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


def test_token_auth_verifier_offline_db_graceful_and_prod_guard():
    bad_settings = Settings(
        app_env="development",
        postgres_uri_app="postgresql+psycopg2://invalid:secret@localhost:9999/down_db",
    )
    verifier = TokenAuthVerifier(bad_settings)
    # Dev token still works offline
    principal = verifier.verify_bearer_token("gml-dev-token-ceo")
    assert principal.user_id == "usr_ceo"
    assert principal.allowed_profiles == ["real", "synth"]

    # Unknown token gracefully handles DB unreachable and raises AuthenticationError (401)
    with pytest.raises(AuthenticationError):
        verifier.verify_bearer_token("non-existent-session-token")

    # Production guard still blocks dev tokens
    prod_settings = Settings(
        app_env="production",
        llm_provider="ollama",
        llm_tier="free",
        postgres_uri_app="postgresql+psycopg2://invalid:secret@localhost:9999/down_db",
    )
    prod_verifier = TokenAuthVerifier(prod_settings)
    with pytest.raises(AuthenticationError):
        prod_verifier.verify_bearer_token("gml-dev-token-ceo")
