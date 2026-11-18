"""Integration tests for /v1/admin/* endpoints, monthly simulation runner, and CLI scripts (Task 3).

Specifications:
- Design §5.4, §5.7, §5.8
- Plan Task 3
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.api import deps
from app.api.deps import get_kpi_cache, reset_kpi_cache, reset_rate_limiter
from app.api.main import create_app
from app.core.config import get_settings
from app.services.iam_service import create_session, create_user
from db.apply_db import get_admin_engine, get_app_engine, get_iam_engine

V2_DIR = Path(__file__).resolve().parent.parent.parent

TEST_USERNAMES = (
    "t3_admin_1",
    "t3_admin_2",
    "t3_managed_user",
    "t3_cli_admin",
    "t3_audit_user",
)


@pytest.fixture(autouse=True)
def clean_singletons_and_test_rows(monkeypatch: pytest.MonkeyPatch):
    """Isolate singletons, offline mock LLM, and clean up Task 3 test rows."""
    monkeypatch.setenv("GOOGLE_API_KEY", "mock_offline")
    get_settings.cache_clear()
    reset_rate_limiter()
    reset_kpi_cache()
    deps.reset_login_rate_limiter()

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
                        "OR user_id IN (SELECT user_id FROM iam.app_user WHERE lower(username) = ANY(:names)) "
                        "OR (event_type = 'simulation_triggered' AND actor_user_id = 'usr_admin')"
                    ),
                    {"names": list(TEST_USERNAMES)},
                )
                conn.execute(
                    sa.text("DELETE FROM iam.app_user WHERE lower(username) = ANY(:names)"),
                    {"names": list(TEST_USERNAMES)},
                )
                conn.execute(
                    sa.text("DELETE FROM app.job_heartbeat WHERE job_name = 'monthly_simulation'")
                )
                conn.execute(
                    sa.text("DELETE FROM app.audit_log WHERE request_id LIKE 'req-t3-%'")
                )
        except Exception:
            pass

    _clean()
    yield
    _clean()
    reset_rate_limiter()
    reset_kpi_cache()
    deps.reset_login_rate_limiter()
    get_settings.cache_clear()


@pytest.fixture
def iam_eng():
    return get_iam_engine()


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer gml-dev-token-admin"}


def test_non_admin_cannot_call_any_admin_or_simulation_endpoint(client):
    # Unauthenticated -> 401
    assert client.get("/v1/admin/users").status_code == 401

    non_admin_tokens = [
        ("ceo", "gml-dev-token-ceo"),
        ("ke_toan_truong", "gml-dev-token-ktt"),
        ("quan_ly_kho", "gml-dev-token-kho"),
    ]
    endpoints = [
        ("GET", "/v1/admin/users", None),
        ("POST", "/v1/admin/users", {"username": "x_nope", "display_name": "Nope", "role": "ceo"}),
        ("PATCH", "/v1/admin/users/usr_ceo", {"display_name": "Hacked"}),
        ("POST", "/v1/admin/users/usr_ceo/reset-password", None),
        ("POST", "/v1/admin/users/usr_ceo/unlock", None),
        ("POST", "/v1/admin/users/usr_ceo/revoke-sessions", None),
        ("GET", "/v1/admin/sessions", None),
        ("DELETE", "/v1/admin/sessions/999999", None),
        ("GET", "/v1/admin/auth-events", None),
        ("GET", "/v1/admin/simulation/status", None),
        ("POST", "/v1/admin/simulation/run", {}),
    ]

    app_eng = get_app_engine(profile="real")
    for role_name, token in non_admin_tokens:
        for method, path, payload in endpoints:
            req_id = f"req-t3-forbid-{role_name}-{uuid.uuid4().hex[:6]}"
            kwargs = {"json": payload} if payload is not None else {}
            res = client.request(
                method,
                path,
                headers={"Authorization": f"Bearer {token}", "X-Request-ID": req_id},
                **kwargs,
            )
            assert res.status_code == 403, f"{role_name} on {method} {path} got {res.status_code}: {res.text}"
            assert res.json()["error"]["code"] == "FORBIDDEN"

            with app_eng.connect() as conn:
                audit_row = conn.execute(
                    sa.text("SELECT role, query FROM app.audit_log WHERE request_id = :rid"),
                    {"rid": req_id},
                ).fetchone()
            assert audit_row is not None
            assert audit_row.role == role_name
            assert "FORBIDDEN" in (audit_row.query or "")


def test_admin_create_update_reset_unlock_and_instant_revoke(client, iam_eng, admin_headers):
    # 1. Create admin1 and admin2 (to test self-lockout and last-admin protection via real IAM sessions)
    admin1, admin1_pw = create_user(
        iam_eng,
        username="t3_admin_1",
        display_name="Admin One",
        role="quan_tri_he_thong",
        password="AdminOnePass@2026",
        must_change_password=False,
    )
    admin2, admin2_pw = create_user(
        iam_eng,
        username="t3_admin_2",
        display_name="Admin Two",
        role="quan_tri_he_thong",
        password="AdminTwoPass@2026",
        must_change_password=False,
    )
    a1_login = client.post("/v1/auth/login", json={"username": "t3_admin_1", "password": admin1_pw})
    assert a1_login.status_code == 200
    a1_hdr = {"Authorization": f"Bearer {a1_login.json()['access_token']}"}

    a2_login = client.post("/v1/auth/login", json={"username": "t3_admin_2", "password": admin2_pw})
    assert a2_login.status_code == 200
    a2_hdr = {"Authorization": f"Bearer {a2_login.json()['access_token']}"}

    # 2. POST /v1/admin/users -> 201 with temporary_password
    create_res = client.post(
        "/v1/admin/users",
        headers=a1_hdr,
        json={
            "username": "t3_managed_user",
            "display_name": "Managed User",
            "email": "managed@gominhlong.local",
            "role": "ke_toan_truong",
            "allowed_profiles": ["real", "synth"],
        },
    )
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    managed_id = created["user"]["user_id"]
    temp_pw = created["temporary_password"]
    assert len(temp_pw) >= 10
    assert created["user"]["must_change_password"] is True
    assert "password_hash" not in created["user"]

    # Duplicate username -> 409 USER_CONFLICT
    dup_res = client.post(
        "/v1/admin/users",
        headers=a1_hdr,
        json={"username": "T3_MANAGED_USER", "display_name": "Dup", "role": "ceo"},
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "USER_CONFLICT"

    # Weak explicit password -> 422 PASSWORD_POLICY_ERROR
    weak_res = client.post(
        "/v1/admin/users",
        headers=a1_hdr,
        json={
            "username": "t3_audit_user",
            "display_name": "Weak Pw",
            "role": "ceo",
            "password": "minhlong123",
        },
    )
    assert weak_res.status_code == 422
    assert weak_res.json()["error"]["code"] == "PASSWORD_POLICY_ERROR"

    # 3. GET /v1/admin/users with filters
    list_res = client.get("/v1/admin/users?q=t3_managed&role=ke_toan_truong&is_active=true", headers=a1_hdr)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["users"][0]["user_id"] == managed_id

    # 4. Managed user logs in with temp password & changes password
    u_login = client.post("/v1/auth/login", json={"username": "t3_managed_user", "password": temp_pw})
    assert u_login.status_code == 200
    u_hdr = {"Authorization": f"Bearer {u_login.json()['access_token']}"}
    new_pw = "GoWoodSafePass@2026"
    cp_res = client.post(
        "/v1/auth/change-password",
        headers=u_hdr,
        json={"current_password": temp_pw, "new_password": new_pw},
    )
    assert cp_res.status_code == 200, cp_res.text

    # 5. PATCH role / allowed_profiles revokes active session immediately
    patch_res = client.patch(
        f"/v1/admin/users/{managed_id}",
        headers=a1_hdr,
        json={"display_name": "Managed User Updated", "role": "quan_ly_kho", "allowed_profiles": ["real"]},
    )
    assert patch_res.status_code == 200, patch_res.text
    assert patch_res.json()["role"] == "quan_ly_kho"
    assert patch_res.json()["allowed_profiles"] == ["real"]
    assert client.get("/v1/auth/me", headers=u_hdr).status_code == 401

    # 6. Lock user via 5 bad attempts -> admin unlock -> login works
    for _ in range(5):
        client.post("/v1/auth/login", json={"username": "t3_managed_user", "password": "WrongPassword99!"})
    assert client.post("/v1/auth/login", json={"username": "t3_managed_user", "password": new_pw}).status_code == 423

    unlock_res = client.post(f"/v1/admin/users/{managed_id}/unlock", headers=a1_hdr)
    assert unlock_res.status_code == 200
    assert unlock_res.json()["failed_login_count"] == 0
    assert unlock_res.json()["locked_until"] is None

    u_login2 = client.post("/v1/auth/login", json={"username": "t3_managed_user", "password": new_pw})
    assert u_login2.status_code == 200
    u_hdr2 = {"Authorization": f"Bearer {u_login2.json()['access_token']}"}

    # 7. GET /v1/admin/sessions & DELETE /v1/admin/sessions/{session_id}
    sess_list = client.get(f"/v1/admin/sessions?user_id={managed_id}", headers=a1_hdr)
    assert sess_list.status_code == 200
    assert sess_list.json()["total"] == 1
    sid = sess_list.json()["sessions"][0]["session_id"]

    del_res = client.delete(f"/v1/admin/sessions/{sid}", headers=a1_hdr)
    assert del_res.status_code == 200
    assert del_res.json() == {"revoked": True}
    assert client.get("/v1/auth/me", headers=u_hdr2).status_code == 401

    # Deleting already-revoked session -> 404 SESSION_NOT_FOUND
    del_again = client.delete(f"/v1/admin/sessions/{sid}", headers=a1_hdr)
    assert del_again.status_code == 404
    assert del_again.json()["error"]["code"] == "SESSION_NOT_FOUND"

    # 8. POST /v1/admin/users/{user_id}/revoke-sessions & reset-password
    tok3, _ = create_session(iam_eng, user_id=managed_id)
    u_hdr3 = {"Authorization": f"Bearer {tok3}"}

    rev_all = client.post(f"/v1/admin/users/{managed_id}/revoke-sessions", headers=a1_hdr)
    assert rev_all.status_code == 200
    assert rev_all.json() == {"user_id": managed_id, "revoked_count": 1}
    assert client.get("/v1/auth/me", headers=u_hdr3).status_code == 401

    tok4, _ = create_session(iam_eng, user_id=managed_id)
    u_hdr4 = {"Authorization": f"Bearer {tok4}"}
    reset_res = client.post(f"/v1/admin/users/{managed_id}/reset-password", headers=a1_hdr)
    assert reset_res.status_code == 200
    assert reset_res.json()["user_id"] == managed_id
    assert len(reset_res.json()["temporary_password"]) >= 10
    assert client.get("/v1/auth/me", headers=u_hdr4).status_code == 401

    # 9. Self-lockout (409 SELF_LOCKOUT) & last-admin protection (409 LAST_ADMIN_PROTECTED)
    self_dis = client.patch(f"/v1/admin/users/{admin1['user_id']}", headers=a1_hdr, json={"is_active": False})
    assert self_dis.status_code == 409
    assert self_dis.json()["error"]["code"] == "SELF_LOCKOUT"

    # Disable admin2 (now admin1 is last active admin) -> admin2's session revoked, then dev admin cannot disable admin1
    assert client.patch(f"/v1/admin/users/{admin2['user_id']}", headers=a1_hdr, json={"is_active": False}).status_code == 200
    assert client.get("/v1/auth/me", headers=a2_hdr).status_code == 401
    last_dis = client.patch(f"/v1/admin/users/{admin1['user_id']}", headers=admin_headers, json={"is_active": False})
    assert last_dis.status_code == 409
    assert last_dis.json()["error"]["code"] == "LAST_ADMIN_PROTECTED"

    # 10. 404 USER_NOT_FOUND checks
    assert client.patch("/v1/admin/users/u_does_not_exist", headers=a1_hdr, json={"display_name": "X"}).status_code == 404
    assert client.post("/v1/admin/users/u_does_not_exist/reset-password", headers=a1_hdr).status_code == 404
    assert client.post("/v1/admin/users/u_does_not_exist/unlock", headers=a1_hdr).status_code == 404
    assert client.post("/v1/admin/users/u_does_not_exist/revoke-sessions", headers=a1_hdr).status_code == 404

    # 11. GET /v1/admin/auth-events
    ev_res = client.get(f"/v1/admin/auth-events?user_id={managed_id}&limit=50", headers=a1_hdr)
    assert ev_res.status_code == 200
    ev_body = ev_res.json()
    assert ev_body["total"] >= 3
    assert any(e["event_type"] == "password_reset_by_admin" for e in ev_body["events"])


def test_admin_simulation_run_updates_heartbeat_clears_cache_and_writes_event(monkeypatch, client, admin_headers):
    from app.api.routers import admin as admin_router

    # Seed a sentinel KPI cache entry to verify cache.clear() is called
    cache = get_kpi_cache(get_settings())
    cache.set(("synth", "ceo", "du_no_ngan_han", "2026-07-31"), {"value": 123.0})
    assert len(cache) == 1

    called_seeds: list[int] = []

    def fake_generate(seed: int = 42, **_kwargs):
        called_seeds.append(seed)
        return {f"synthetic.tbl_{i}": f"sha_{i}" for i in range(20)}

    monkeypatch.setattr(admin_router, "generate_synthetic_warehouse", fake_generate)

    # Empty body works as well as explicit JSON
    res = client.post("/v1/admin/simulation/run", headers=admin_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "ok"
    assert body["tables_generated"] == 20
    assert body["duration_ms"] >= 0
    assert body["run_at"]
    assert called_seeds == [42]
    assert len(get_kpi_cache(get_settings())) == 0

    # Explicit seed payload works
    res2 = client.post("/v1/admin/simulation/run", headers=admin_headers, json={"seed": 99})
    assert res2.status_code == 200
    assert called_seeds == [42, 99]

    # Check app.job_heartbeat
    app_eng = get_app_engine(profile="real")
    with app_eng.connect() as conn:
        hb = conn.execute(
            sa.text(
                "SELECT job_name, status, duration_ms, message FROM app.job_heartbeat "
                "WHERE job_name = 'monthly_simulation' ORDER BY created_at DESC, id DESC LIMIT 1"
            )
        ).fetchone()
    assert hb is not None
    assert hb.status == "ok"

    # Check iam.auth_event
    iam_eng = get_iam_engine()
    with iam_eng.connect() as conn:
        ev = conn.execute(
            sa.text(
                "SELECT event_type, actor_user_id FROM iam.auth_event "
                "WHERE event_type = 'simulation_triggered' ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()
    assert ev is not None
    assert ev.actor_user_id == "usr_admin"

    # GET /v1/admin/simulation/status reflects latest heartbeat
    status_res = client.get("/v1/admin/simulation/status", headers=admin_headers)
    assert status_res.status_code == 200, status_res.text
    st_body = status_res.json()
    assert st_body["last_status"] == "ok"
    assert st_body["last_run_at"] is not None
    assert isinstance(st_body["checksum_file_exists"], bool)

    # Failure path records status='error' heartbeat and returns 500 SIMULATION_FAILED
    def broken_generate(seed: int = 42, **_kwargs):
        raise RuntimeError("simulated warehouse failure")

    monkeypatch.setattr(admin_router, "generate_synthetic_warehouse", broken_generate)
    fail_res = client.post("/v1/admin/simulation/run", headers=admin_headers, json={"seed": 7})
    assert fail_res.status_code == 500
    assert fail_res.json()["error"]["code"] == "SIMULATION_FAILED"

    status_after_fail = client.get("/v1/admin/simulation/status", headers=admin_headers)
    assert status_after_fail.status_code == 200
    assert status_after_fail.json()["last_status"] == "error"


def test_no_password_hash_or_raw_token_leaked_in_admin_or_audit_logs(client, admin_headers):
    req_create = f"req-t3-audit-create-{uuid.uuid4().hex[:6]}"
    c_res = client.post(
        "/v1/admin/users",
        headers={**admin_headers, "X-Request-ID": req_create},
        json={
            "username": "t3_audit_user",
            "display_name": "Audit Check User",
            "role": "ceo",
            "password": "AuditStrongPass@2026",
        },
    )
    assert c_res.status_code == 201
    uid = c_res.json()["user"]["user_id"]
    temp_pw = c_res.json()["temporary_password"]

    # Login to produce raw token & auth_event
    l_res = client.post(
        "/v1/auth/login",
        json={"username": "t3_audit_user", "password": temp_pw},
    )
    assert l_res.status_code == 200
    raw_token = l_res.json()["access_token"]

    req_reset = f"req-t3-audit-reset-{uuid.uuid4().hex[:6]}"
    r_res = client.post(
        f"/v1/admin/users/{uid}/reset-password",
        headers={**admin_headers, "X-Request-ID": req_reset},
    )
    assert r_res.status_code == 200
    reset_pw = r_res.json()["temporary_password"]

    users_payload = client.get("/v1/admin/users?q=t3_audit_user", headers=admin_headers).text
    sessions_payload = client.get("/v1/admin/sessions", headers=admin_headers).text
    events_payload = client.get(f"/v1/admin/auth-events?user_id={uid}", headers=admin_headers).text

    for payload_str in (users_payload, sessions_payload, events_payload):
        assert "password_hash" not in payload_str
        assert "$argon2" not in payload_str
        assert "token_hash" not in payload_str
        assert temp_pw not in payload_str
        assert reset_pw not in payload_str
        assert raw_token not in payload_str

    # Check app.audit_log rows & iam.auth_event rows
    app_eng = get_app_engine(profile="real")
    with app_eng.connect() as conn:
        audit_rows = conn.execute(
            sa.text("SELECT request_id, query, sql_executed FROM app.audit_log WHERE request_id IN (:r1, :r2)"),
            {"r1": req_create, "r2": req_reset},
        ).fetchall()
    assert len(audit_rows) == 2
    for row in audit_rows:
        combined = f"{row.query or ''} {row.sql_executed or ''}"
        for secret in (temp_pw, reset_pw, raw_token, "$argon2"):
            assert secret not in combined

    iam_eng = get_iam_engine()
    with iam_eng.connect() as conn:
        ev_rows = conn.execute(
            sa.text("SELECT detail FROM iam.auth_event WHERE user_id = :uid"),
            {"uid": uid},
        ).fetchall()
    for row in ev_rows:
        detail_str = json.dumps(row.detail or {}, ensure_ascii=False)
        for secret in (temp_pw, reset_pw, raw_token, "$argon2"):
            assert secret not in detail_str


def test_seed_demo_users_refuses_production_env(monkeypatch, iam_eng):
    from scripts import create_admin, seed_demo_users

    # 1. Production refusal via function call
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        seed_demo_users.run_seed_demo_users()

    # 2. Production refusal via CLI subprocess exits non-zero
    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env["LLM_PROVIDER"] = "ollama"
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.seed_demo_users"],
        cwd=str(V2_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0

    # 3. create_admin idempotency check
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    first = create_admin.create_admin_account(
        iam_eng,
        username="t3_cli_admin",
        display_name="CLI Admin",
        email="cli.admin@gominhlong.local",
    )
    assert first["created"] is True
    assert first["user"]["role"] == "quan_tri_he_thong"
    assert len(first["temporary_password"]) >= 10

    second = create_admin.create_admin_account(
        iam_eng,
        username="t3_cli_admin",
        display_name="CLI Admin",
        email="cli.admin@gominhlong.local",
    )
    assert second["created"] is False
    assert second["temporary_password"] is None
