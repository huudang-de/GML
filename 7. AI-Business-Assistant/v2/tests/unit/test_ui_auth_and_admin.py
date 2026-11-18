"""Unit test suite for Streamlit Login Gate, F5 Cookie Persistence, Role-Locked Sidebar & 4-Tab Admin Panel (Task 4).

Covers:
1. test_unauthenticated_user_sees_login_form_only_and_no_role_selector
2. test_login_sets_session_and_locks_ktt_role_ignoring_query_role
3. test_f5_reload_restores_session_from_cookie_and_clears_expired_cookie
4. test_forced_password_change_screen_blocks_main_app_until_changed
5. test_admin_login_renders_4_tab_admin_panel_without_business_screens
6. test_ui_layer_still_has_zero_server_imports
"""

import ast
from pathlib import Path
from typing import Any
import httpx
import pytest
import sqlalchemy as sa
from starlette.testclient import TestClient
import streamlit as st
from streamlit.testing.v1 import AppTest

from app.api import create_app, deps
from app.api.deps import reset_kpi_cache, reset_rate_limiter
from app.core.config import get_settings
from app.services import iam_service
from app.ui.api_client import (
    get_require_login_for_testing,
    set_default_transport_for_testing,
    set_require_login_for_testing,
)
from app.ui.components.login_view import COOKIE_NAME
from db.apply_db import get_admin_engine, get_iam_engine

APP_PATH = str(Path(__file__).resolve().parent.parent.parent / "app" / "ui" / "streamlit_app.py")

TEST_USERNAMES = (
    "t4_ktt_user",
    "t4_temp_user",
    "t4_f5_user",
    "t4_admin_user",
    "t4_created_user",
)


class RequestSpy:
    """Records HTTP requests handled through mock transport for assertion."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def clear(self) -> None:
        self.requests.clear()

    def last(self, method: str, path_prefix: str) -> httpx.Request | None:
        for r in reversed(self.requests):
            if r.method.upper() == method.upper() and r.url.path.startswith(path_prefix):
                return r
        return None

    def all(self, method: str, path_prefix: str) -> list[httpx.Request]:
        return [
            r
            for r in self.requests
            if r.method.upper() == method.upper() and r.url.path.startswith(path_prefix)
        ]


@pytest.fixture
def spy_requests() -> RequestSpy:
    """Fixture providing HTTP request spy."""
    return RequestSpy()


@pytest.fixture
def cookie_jar(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Patch st.context.cookies so tests can simulate browser cookies on F5 reload."""
    jar: dict[str, str] = {}
    monkeypatch.setattr(type(st.context), "cookies", property(lambda self: dict(jar)))
    return jar


@pytest.fixture(autouse=True)
def setup_auth_api_transport(
    spy_requests: RequestSpy,
    cookie_jar: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    """Wire Streamlit AppTest to in-process FastAPI app with login enforcement enabled."""
    monkeypatch.setenv("GOOGLE_API_KEY", "mock_offline")
    get_settings.cache_clear()
    reset_rate_limiter()
    reset_kpi_cache()
    if hasattr(deps, "reset_login_rate_limiter"):
        deps.reset_login_rate_limiter()

    def _clean() -> None:
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

    app = create_app()
    tc = TestClient(app)

    def handler(request: httpx.Request) -> httpx.Response:
        spy_requests.requests.append(request)
        resp = tc.request(
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
            content=request.read(),
        )
        return httpx.Response(
            status_code=resp.status_code,
            headers=resp.headers,
            content=resp.content,
            request=request,
        )

    mock_transport = httpx.MockTransport(handler)
    set_default_transport_for_testing(mock_transport)
    set_require_login_for_testing(True)

    yield mock_transport

    set_require_login_for_testing(None)
    set_default_transport_for_testing(None)
    _clean()
    reset_rate_limiter()
    reset_kpi_cache()
    if hasattr(deps, "reset_login_rate_limiter"):
        deps.reset_login_rate_limiter()
    get_settings.cache_clear()


@pytest.fixture
def auth_app_test():
    """Factory creating AppTest instances with optional query params."""

    def _create(query_params: dict[str, str] | None = None) -> AppTest:
        at = AppTest.from_file(APP_PATH)
        if query_params:
            for k, v in query_params.items():
                at.query_params[k] = v
        return at

    return _create


@pytest.fixture
def iam_user_factory():
    """Create temporary IAM accounts in the real DB for UI tests."""
    eng = get_iam_engine()

    def _make(
        *,
        username: str,
        display_name: str,
        role: str,
        password: str = "StrongPass@2026",
        allowed_profiles: list[str] | None = None,
        must_change_password: bool = False,
        email: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        return iam_service.create_user(
            eng,
            username=username,
            display_name=display_name,
            role=role,
            allowed_profiles=allowed_profiles if allowed_profiles is not None else ["real", "synth"],
            email=email,
            password=password,
            must_change_password=must_change_password,
        )

    return _make


def _submit_login(at: AppTest, username: str, password: str) -> None:
    """Fill login form inputs and click 'Đăng nhập'."""
    u_box = next((t for t in at.text_input if t.key == "login_username"), at.text_input[0])
    p_box = next((t for t in at.text_input if t.key == "login_password"), at.text_input[1])
    u_box.set_value(username)
    p_box.set_value(password)
    login_btn = next(b for b in at.button if "Đăng nhập" in b.label)
    login_btn.click().run(timeout=35)


def test_unauthenticated_user_sees_login_form_only_and_no_role_selector(auth_app_test):
    """Unauthenticated visitor sees branded login gate only, no role selector, and ?role=ceo is ignored."""
    assert get_require_login_for_testing() is True
    at = auth_app_test(query_params={"role": "ceo"})
    at.run(timeout=35)
    assert not at.exception

    assert not any(s.key == "role_selector" for s in at.selectbox)
    assert not any(r.key == "screen_selector" for r in at.radio)
    assert any("Đăng nhập" in b.label for b in at.button)

    all_md = " ".join(m.value for m in at.markdown)
    assert "GỖ MINH LONG" in all_md
    assert "Tổng Giám đốc" not in all_md


def test_login_sets_session_and_locks_ktt_role_ignoring_query_role(
    auth_app_test,
    iam_user_factory,
    spy_requests: RequestSpy,
):
    """Logging in as KTT locks role='ke_toan_truong' even when ?role=ceo is present, and preserves Quick Ask params."""
    _, pw = iam_user_factory(
        username="t4_ktt_user",
        display_name="Trần Thị Kế Toán",
        role="ke_toan_truong",
        allowed_profiles=["real"],
        must_change_password=False,
    )

    at = auth_app_test(query_params={"role": "ceo", "dashboard": "tai_chinh", "kpi": "du_no_ngan_han"})
    at.run(timeout=35)
    assert not at.exception

    _submit_login(at, "t4_ktt_user", pw)
    assert not at.exception

    assert at.session_state["auth_token"]
    assert at.session_state["auth_user"]["role"] == "ke_toan_truong"

    # Role selector is completely gone; single allowed profile hides profile radio
    assert not any(s.key == "role_selector" for s in at.selectbox)
    assert not any(r.key == "profile_selector" for r in at.radio)

    # Sidebar & masthead display real identity + Vietnamese KTT role, never CEO
    sidebar_md = " ".join(m.value for m in at.sidebar.markdown)
    main_md = " ".join(m.value for m in at.markdown)
    assert "Trần Thị Kế Toán" in sidebar_md
    assert "Kế toán trưởng" in sidebar_md
    assert "Kế toán trưởng" in main_md
    assert "Tổng Giám đốc" not in main_md

    # Pending Quick Ask params restored after login -> landed on Chat screen
    assert len(at.chat_input) > 0
    assert "Dư nợ ngắn hạn" in " ".join(i.value for i in at.info)

    # Verify API calls used the real session token, not gml-dev-token-ceo
    kpi_req = spy_requests.last("GET", "/v1/kpi/du_no_ngan_han")
    assert kpi_req is not None
    assert kpi_req.headers.get("authorization") == f"Bearer {at.session_state['auth_token']}"


def test_f5_reload_restores_session_from_cookie_and_clears_expired_cookie(
    auth_app_test,
    iam_user_factory,
    cookie_jar: dict[str, str],
    spy_requests: RequestSpy,
):
    """F5 reload reads gml_session cookie and restores via GET /v1/auth/me; expired cookie clears and shows flash."""
    user, _ = iam_user_factory(
        username="t4_f5_user",
        display_name="Nguyễn Văn F5",
        role="ceo",
        allowed_profiles=["real", "synth"],
        must_change_password=False,
    )
    eng = get_iam_engine()
    raw_token, _ = iam_service.create_session(eng, user_id=user["user_id"], client_ip="127.0.0.1")

    # 1. Valid cookie restores session cleanly without login form
    cookie_jar[COOKIE_NAME] = raw_token
    at_reloaded = auth_app_test()
    at_reloaded.run(timeout=35)
    assert not at_reloaded.exception
    assert at_reloaded.session_state["auth_token"] == raw_token
    assert at_reloaded.session_state["auth_user"]["username"] == "t4_f5_user"
    assert not any("Đăng nhập" in b.label for b in at_reloaded.button)
    assert spy_requests.last("GET", "/v1/auth/me") is not None

    # 2. Expired / revoked cookie clears session and shows Vietnamese flash message on login gate
    iam_service.revoke_session(eng, raw_token=raw_token, reason="admin_revoked")
    spy_requests.clear()

    at_expired = auth_app_test()
    at_expired.run(timeout=35)
    assert not at_expired.exception
    assert "auth_token" not in at_expired.session_state or not at_expired.session_state["auth_token"]
    assert any("Đăng nhập" in b.label for b in at_expired.button)
    flash_msgs = " ".join([e.value for e in at_expired.error] + [w.value for w in at_expired.warning])
    assert "Phiên đăng nhập đã hết hạn" in flash_msgs


def test_forced_password_change_screen_blocks_main_app_until_changed(
    auth_app_test,
    iam_user_factory,
    spy_requests: RequestSpy,
):
    """Accounts with must_change_password=True are blocked from business screens until password is updated."""
    _, temp_pw = iam_user_factory(
        username="t4_temp_user",
        display_name="Nhân Viên Mới",
        role="quan_ly_kho",
        allowed_profiles=["real", "synth"],
        must_change_password=True,
    )

    at = auth_app_test()
    at.run(timeout=35)
    assert not at.exception

    _submit_login(at, "t4_temp_user", temp_pw)
    assert not at.exception

    # Blocked from main app screens
    assert not any(r.key == "screen_selector" for r in at.radio)
    assert not any(b.key == "overview_q_0" for b in at.button)
    assert len(at.chat_input) == 0
    assert any("Đăng xuất" in b.label for b in at.sidebar.button)

    # NIST 800-63B hint + forced password inputs displayed
    all_text = " ".join(
        [m.value for m in at.markdown]
        + [i.value for i in at.info]
        + [w.value for w in at.warning]
        + [c.value for c in at.caption]
    )
    assert "10–128 ký tự" in all_text

    cur_box = next(t for t in at.text_input if t.key == "cp_current_password")
    new_box = next(t for t in at.text_input if t.key == "cp_new_password")
    cfm_box = next(t for t in at.text_input if t.key == "cp_confirm_password")
    cur_box.set_value(temp_pw)
    new_box.set_value("WoodFactory#2026")
    cfm_box.set_value("WoodFactory#2026")

    submit_cp = next(b for b in at.button if "Đổi mật khẩu" in b.label)
    submit_cp.click().run(timeout=35)
    assert not at.exception

    assert spy_requests.last("POST", "/v1/auth/change-password") is not None
    assert at.session_state["auth_user"]["must_change_password"] is False
    # Main app is now accessible
    assert any(r.key == "screen_selector" for r in at.radio)


def test_admin_login_renders_4_tab_admin_panel_without_business_screens(
    auth_app_test,
    iam_user_factory,
    spy_requests: RequestSpy,
):
    """quan_tri_he_thong sees only Admin sidebar + 4-tab Admin Panel and zero business/KPI screens."""
    _, admin_pw = iam_user_factory(
        username="t4_admin_user",
        display_name="Quản Trị Viên",
        role="quan_tri_he_thong",
        allowed_profiles=["real"],
        must_change_password=False,
    )

    at = auth_app_test()
    at.run(timeout=35)
    assert not at.exception

    _submit_login(at, "t4_admin_user", admin_pw)
    assert not at.exception

    # Zero business screens or role/profile selectors
    assert not any(s.key == "role_selector" for s in at.selectbox)
    assert not any(r.key == "profile_selector" for r in at.radio)
    assert not any(r.key == "screen_selector" for r in at.radio)
    assert len(at.chat_input) == 0

    sidebar_md = " ".join(m.value for m in at.sidebar.markdown)
    assert "Quản Trị Viên" in sidebar_md
    assert "Quản trị hệ thống" in sidebar_md
    assert any("Đổi mật khẩu" in b.label for b in at.sidebar.button)
    assert any("Đăng xuất" in b.label for b in at.sidebar.button)

    # 4 admin tabs rendered
    tab_labels = [t.label for t in at.tabs]
    assert len(tab_labels) == 4
    assert any("Người dùng" in lbl for lbl in tab_labels)
    assert any("Phiên đăng nhập" in lbl for lbl in tab_labels)
    assert any("Mô phỏng" in lbl and "synth" in lbl for lbl in tab_labels)
    assert any("Nhật ký" in lbl for lbl in tab_labels)

    # Admin endpoints called cleanly
    assert spy_requests.last("GET", "/v1/admin/users") is not None
    assert spy_requests.last("GET", "/v1/admin/sessions") is not None
    assert spy_requests.last("GET", "/v1/admin/simulation/status") is not None
    assert spy_requests.last("GET", "/v1/admin/auth-events") is not None


def test_ui_layer_still_has_zero_server_imports():
    """Architectural Boundary AST check: v2/app/ui/**/*.py must never import app.services, app.agents, app.knowledge, or db."""
    ui_dir = Path(__file__).resolve().parent.parent.parent / "app" / "ui"
    forbidden_app_modules = {"services", "agents", "knowledge"}

    py_files = list(ui_dir.rglob("*.py"))
    assert len(py_files) >= 5

    for py_file in py_files:
        code = py_file.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                if parts[0] == "db":
                    pytest.fail(f"File {py_file} imports forbidden db module: {node.module}")
                if parts[0] == "app" and len(parts) > 1 and parts[1] in forbidden_app_modules:
                    pytest.fail(f"File {py_file} imports forbidden server layer: {node.module}")

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    if parts[0] == "db":
                        pytest.fail(f"File {py_file} imports forbidden db module: {alias.name}")
                    if parts[0] == "app" and len(parts) > 1 and parts[1] in forbidden_app_modules:
                        pytest.fail(f"File {py_file} imports forbidden server layer: {alias.name}")
