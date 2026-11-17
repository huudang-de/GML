"""Unit test suite for Streamlit UI 5-screen revision (P4r / Task 6).

Covers:
- test_tc_t6_06_default_overview_but_quick_ask_opens_chat
- test_overview_metrics_rendered_for_kho
- test_overview_suggested_chip_navigates_to_chat
- test_tc_t6_07_create_action_from_alert_detail
- test_chat_shows_trend_and_advice_directly_and_pin_button
- test_actions_view_updates_status
- test_ui_does_not_import_server_layers (AST test)
- test_three_roles_render_cleanly_on_synth
"""

import ast
import json
from pathlib import Path
from typing import Any
import pytest
import sqlalchemy as sa
import httpx
from starlette.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app.api import create_app
from app.core.config import get_settings
from app.ui.api_client import set_default_transport_for_testing
from db.apply_db import get_app_engine

APP_PATH = str(Path(__file__).resolve().parent.parent.parent / "app" / "ui" / "streamlit_app.py")


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
            r for r in self.requests
            if r.method.upper() == method.upper() and r.url.path.startswith(path_prefix)
        ]


@pytest.fixture
def spy_requests():
    """Fixture providing HTTP request spy."""
    return RequestSpy()


@pytest.fixture(autouse=True)
def setup_api_transport(spy_requests: RequestSpy, monkeypatch: pytest.MonkeyPatch):
    """Wire Streamlit AppTest to in-process FastAPI application via httpx MockTransport with spy."""
    monkeypatch.setenv("GOOGLE_API_KEY", "mock_offline")
    get_settings.cache_clear()
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
    yield mock_transport
    set_default_transport_for_testing(None)
    get_settings.cache_clear()


@pytest.fixture
def app_test_factory():
    """Factory creating AppTest instances configured with role, profile, screen, or extra params."""
    def _create(
        role: str = "ceo",
        profile: str = "real",
        screen: str | None = None,
        query_params: dict[str, str] | None = None,
    ) -> AppTest:
        at = AppTest.from_file(APP_PATH)
        at.query_params["role"] = role
        at.query_params["profile"] = profile
        if screen is not None:
            at.query_params["screen"] = screen
        if query_params:
            for k, v in query_params.items():
                at.query_params[k] = v
        return at

    return _create


@pytest.fixture
def seeded_alert():
    """Seed an unacknowledged critical alert with approved action evidence into app.alert_event."""
    engine = get_app_engine(profile="real")
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id = 'AL-TEST-P4R'"))
        evidence_json = json.dumps({
            "period": "2026-07",
            "approved_actions": [
                "Kích hoạt phương án khẩn cấp: ngừng toàn bộ các khoản giải ngân mới chưa cấp thiết."
            ],
            "series": [
                {"period": "2026-05", "value": 0.85},
                {"period": "2026-06", "value": 0.90},
                {"period": "2026-07", "value": 0.95},
            ],
            "coverage_warning": "Dữ liệu hạn mức ngân hàng mới cập nhật đến tháng 7/2026.",
        })
        row = conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (
                    rule_id, kpi_key, severity, message, value, threshold,
                    is_acknowledged, period, evidence, created_at
                ) VALUES (
                    'AL-TEST-P4R', 'ty_le_su_dung_han_muc', 'critical',
                    'Tỷ lệ sử dụng hạn mức tín dụng vượt ngưỡng 90%',
                    0.95, 0.90, false, '2026-07', :evidence, now()
                )
                RETURNING id;
            """),
            {"evidence": evidence_json},
        ).fetchone()
        alert_id = row[0]

    yield alert_id

    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.action_item WHERE source_ref = :ref"), {"ref": str(alert_id)})
        conn.execute(sa.text("DELETE FROM app.alert_event WHERE id = :aid"), {"aid": alert_id})


def test_tc_t6_06_default_overview_but_quick_ask_opens_chat(app_test_factory):
    """TC-T6-06: Default screen without params opens Overview; query params kpi/dashboard open Chat."""
    # 1. No params -> Overview screen
    at = app_test_factory()
    at.run(timeout=35)
    assert not at.exception
    all_markdown = " ".join(m.value for m in at.markdown)
    assert "Chào" in all_markdown or any("Chào" in m.value for m in at.markdown), "Expected Overview greeting"

    # 2. Quick Ask with kpi & dashboard -> Chat screen
    at2 = app_test_factory(query_params={"kpi": "du_no_ngan_han", "dashboard": "tai_chinh"})
    at2.run(timeout=35)
    assert not at2.exception
    assert len(at2.chat_input) > 0, "Expected Chat screen with chat_input present for Quick Ask"


def test_overview_metrics_rendered_for_kho(app_test_factory):
    """Overview screen renders 3 role KPIs for quan_ly_kho on synth profile."""
    at = app_test_factory(role="quan_ly_kho", profile="synth")
    at.run(timeout=35)
    assert not at.exception
    assert len(at.metric) == 3, f"Expected 3 metrics for quan_ly_kho, got {len(at.metric)}"


def test_overview_suggested_chip_navigates_to_chat(app_test_factory):
    """Clicking a suggested question chip in Overview navigates to Chat screen."""
    at = app_test_factory(role="ceo", profile="synth")
    at.run(timeout=35)
    assert not at.exception

    # Find suggested question buttons (chips)
    chip_buttons = [b for b in at.button if b.key and b.key.startswith("overview_q_")]
    assert len(chip_buttons) > 0, "Expected at least one suggested question chip button"

    # Click first chip
    chip_buttons[0].click().run(timeout=35)
    assert not at.exception
    # Should navigate to Chat screen
    assert len(at.chat_input) > 0, "Expected Chat screen after clicking suggested question chip"


def test_tc_t6_07_create_action_from_alert_detail(app_test_factory, seeded_alert, spy_requests: RequestSpy):
    """TC-T6-07: In Alert detail view, clicking 'Tạo hành động' posts to /v1/actions."""
    at = app_test_factory(screen="alerts")
    at.run(timeout=35)
    assert not at.exception

    # Find button key create_action_{seeded_alert}_0
    btn_key = f"create_action_{seeded_alert}_0"
    target_btn = next((b for b in at.button if b.key == btn_key), None)
    assert target_btn is not None, f"Expected button with key '{btn_key}' in alert detail"

    target_btn.click().run(timeout=35)
    assert not at.exception

    last_action_post = spy_requests.last("POST", "/v1/actions")
    assert last_action_post is not None, "Expected POST /v1/actions request"
    body = json.loads(last_action_post.content)
    assert body["source_type"] == "alert"
    assert body["source_ref"] == str(seeded_alert)
    assert body["kpi_key"] == "ty_le_su_dung_han_muc"
    assert body["level"] == "nghiem_trong"


def test_chat_shows_trend_and_advice_directly_and_pin_button(app_test_factory, spy_requests: RequestSpy):
    """Chat displays trend and advice directly (not in expander), and has pin button that calls POST /v1/pins."""
    at = app_test_factory(screen="chat")
    at.run(timeout=35)
    assert not at.exception

    at.chat_input[0].set_value("Dư nợ ngắn hạn hiện tại là bao nhiêu?").run(timeout=35)
    assert not at.exception

    # Expander labels should have SQL and sources, but NOT Trend or Advice
    expander_labels = [exp.label for exp in at.expander]
    assert not any("Xu hướng" in l for l in expander_labels), "Trend must not be in expander"
    assert not any("Gợi ý hành động" in l for l in expander_labels), "Advice must not be in expander"

    # Markdown texts should contain Trend / Advice sections directly
    markdown_texts = " ".join(m.value for m in at.markdown)
    assert "Xu hướng" in markdown_texts or "📈" in markdown_texts
    assert "Gợi ý hành động" in markdown_texts or "💡" in markdown_texts

    # Find pin button
    pin_buttons = [b for b in at.button if b.key and b.key.startswith("pin_")]
    assert len(pin_buttons) > 0, "Expected at least one pin button for kpi_keys in chat turn"

    # Click pin button
    pin_buttons[0].click().run(timeout=35)
    assert not at.exception

    last_pin_post = spy_requests.last("POST", "/v1/pins")
    assert last_pin_post is not None, "Expected POST /v1/pins request"
    pin_body = json.loads(last_pin_post.content)
    assert "kpi_key" in pin_body


def test_actions_view_updates_status(app_test_factory, spy_requests: RequestSpy):
    """Actions view renders items and updates status via PATCH /v1/actions/{id}."""
    engine = get_app_engine(profile="real")
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.action_item WHERE source_ref = 'test-act-ref'"))
        row = conn.execute(
            sa.text("""
                INSERT INTO app.action_item (
                    title, kpi_key, level, source_type, source_ref, assigned_role,
                    status, due_date, note, created_by, created_at, updated_at
                ) VALUES (
                    'Tạm dừng giải ngân mới từ các ngân hàng có tỷ lệ sử dụng trên 80%.',
                    'ty_le_su_dung_han_muc', 'canh_bao', 'alert', 'test-act-ref',
                    'ke_toan_truong', 'open', '2026-08-15', 'Ghi chú test',
                    'ceo', now(), now()
                )
                RETURNING id;
            """)
        ).fetchone()
        act_id = row[0]

    try:
        at = app_test_factory(role="ceo", screen="actions")
        at.run(timeout=35)
        assert not at.exception

        # Find selectbox for this action
        status_box = next((s for s in at.selectbox if s.key == f"action_status_{act_id}"), None)
        assert status_box is not None, f"Expected status selectbox for action {act_id}"

        # Change status to in_progress
        status_box.select("in_progress").run(timeout=35)
        assert not at.exception

        last_patch = spy_requests.last("PATCH", f"/v1/actions/{act_id}")
        assert last_patch is not None, f"Expected PATCH /v1/actions/{act_id}"
        patch_body = json.loads(last_patch.content)
        assert patch_body.get("status") == "in_progress"

    finally:
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.action_item WHERE id = :id"), {"id": act_id})


def test_ui_does_not_import_server_layers():
    """Architectural Boundary AST test: app/ui/**/*.py must not import app.services, app.agents, app.knowledge, or db."""
    ui_dir = Path(__file__).resolve().parent.parent.parent / "app" / "ui"
    forbidden_app_modules = {"services", "agents", "knowledge"}

    for py_file in ui_dir.rglob("*.py"):
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


def test_three_roles_render_cleanly_on_synth(app_test_factory):
    """Synthetic profile renders cleanly across CEO, KTT, and Kho on 4 primary screens."""
    roles = ["ceo", "ke_toan_truong", "quan_ly_kho"]
    screens = ["overview", "alerts", "chat", "actions"]

    for r in roles:
        for s in screens:
            at = app_test_factory(role=r, profile="synth", screen=s)
            at.run(timeout=35)
            assert not at.exception, f"Failed rendering screen '{s}' for role '{r}' on synth"


def test_chat_create_action_preserves_nghiem_trong_level(app_test_factory, spy_requests: RequestSpy):
    """Critical #2: Clicking 'Tạo hành động' on a nghiem_trong advice item in Chat submits level='nghiem_trong' -> 201."""
    engine = get_app_engine(profile="real")
    at = app_test_factory(role="ceo", profile="real", screen="chat")
    at.run(timeout=35)
    assert not at.exception

    # Query ty_le_su_dung_han_muc which exceeds nghiem_trong (>= 0.90) on real data
    at.chat_input[0].set_value("Tỷ lệ sử dụng hạn mức?").run(timeout=35)
    assert not at.exception

    chat_action_btns = [b for b in at.button if b.key and b.key.startswith("create_chat_act_")]
    assert len(chat_action_btns) > 0, "Expected 'Tạo hành động' button on nghiem_trong advice in Chat"

    try:
        chat_action_btns[0].click().run(timeout=35)
        assert not at.exception

        last_post = spy_requests.last("POST", "/v1/actions")
        assert last_post is not None, "Expected POST /v1/actions call from Chat"
        payload = json.loads(last_post.content)
        assert payload["source_type"] == "chat"
        assert payload["kpi_key"] == "ty_le_su_dung_han_muc"
        assert payload["level"] == "nghiem_trong"

        success_msgs = " ".join(s.value for s in at.success)
        assert "Đã tạo hành động" in success_msgs
        assert not at.error
    finally:
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.action_item WHERE source_type = 'chat' AND kpi_key = 'ty_le_su_dung_han_muc'"))


def test_cross_screen_navigation_persists_with_screen_query_param(app_test_factory):
    """Important #2: With ?screen=overview set, navigating via chip and interacting on Chat stays on Chat."""
    at = app_test_factory(role="ceo", profile="synth", screen="overview")
    at.run(timeout=35)
    assert not at.exception

    chip_buttons = [b for b in at.button if b.key and b.key.startswith("overview_q_")]
    assert len(chip_buttons) > 0

    # Click chip -> navigates to Chat and executes pending_query
    chip_buttons[0].click().run(timeout=35)
    assert not at.exception
    assert len(at.chat_input) > 0, "Expected navigation to Chat after clicking chip"

    # Interact again on Chat (submit another question) while ?screen=overview is still in query_params
    at.chat_input[0].set_value("Dư nợ ngắn hạn hiện tại là bao nhiêu?").run(timeout=35)
    assert not at.exception
    assert len(at.chat_input) > 0, "Must stay on Chat screen instead of reverting to ?screen=overview"
