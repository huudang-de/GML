"""Unit test suite for Streamlit UI v2.0 (TC-T6-01..04 and Power BI Quick Ask).

Specifications:
- TC-T6-01: Chat view displays dual output: summary text, figures table, SQL expander, RAG sources list, confidence badge.
- TC-T6-02: Profile synth (or URL param profile=synth) ALWAYS renders warning banner containing exact substring 'DỮ LIỆU MÔ PHỎNG'.
- TC-T6-03: In Alert Center, clicking 'Đã xem' calls POST /v1/alerts/{id}/ack via the API client and updates status to 'Đã xác nhận'.
- TC-T6-04: Thumbs-down feedback + note submits POST /v1/feedback and persists to app.feedback with matching request_id.
- Power BI Quick Ask integration: reading URL params ?dashboard=...&kpi=... pre-populates the query context.
"""

from pathlib import Path
import pytest
import sqlalchemy as sa
import httpx
from starlette.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app.api import create_app
from app.ui.api_client import set_default_transport_for_testing
from db.apply_db import get_app_engine

APP_PATH = str(Path(__file__).resolve().parent.parent.parent / "app" / "ui" / "streamlit_app.py")


@pytest.fixture(autouse=True)
def setup_api_transport():
    """Wire Streamlit AppTest to in-process FastAPI application via httpx MockTransport."""
    app = create_app()
    tc = TestClient(app)

    def handler(request: httpx.Request) -> httpx.Response:
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


def test_tc_t6_01_chat_displays_dual_output():
    """TC-T6-01: User submits query in AppTest; verifies dual output: summary text, figures table, SQL expander, sources, and confidence badge."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=35)
    assert not at.exception

    # User submits query
    at.chat_input[0].set_value("Dư nợ ngắn hạn hiện tại là bao nhiêu?").run(timeout=35)
    assert not at.exception

    # 1. Summary text
    markdown_texts = [m.value for m in at.markdown]
    assert any("Dư nợ ngắn hạn" in text for text in markdown_texts), "Expected summary text to mention 'Dư nợ ngắn hạn'"

    # 2. Figures table / dataframe containing figure details
    all_table_text = " ".join([str(df.value) for df in at.dataframe] + [str(t.value) for t in at.table] + markdown_texts)
    assert "236" in all_table_text, "Expected figure value ~236 tỷ in figures table or markdown"

    # 3. SQL expander containing SQL executed
    expander_labels = [exp.label for exp in at.expander]
    assert any("SQL" in label or "sql" in label.lower() for label in expander_labels), "Expected SQL expander"
    code_snippets = [c.value for c in at.code]
    assert any("SELECT" in c and "ai_v_no_vay" in c for c in code_snippets), "Expected SQL code with ai_v_no_vay"

    # 4. Confidence badge
    caption_texts = [c.value for c in at.caption]
    all_badges = " ".join(caption_texts + markdown_texts)
    assert "tin cậy" in all_badges or "confidence" in all_badges.lower() or "%" in all_badges, "Expected confidence badge"


def test_tc_t6_02_synthetic_profile_always_renders_simulation_banner():
    """TC-T6-02: Profile synth (or URL param profile=synth) ALWAYS renders warning banner containing exact substring 'DỮ LIỆU MÔ PHỎNG'."""
    at = AppTest.from_file(APP_PATH)
    at.query_params["profile"] = "synth"
    at.run(timeout=35)
    assert not at.exception

    # Before chat: warning banner must contain 'DỮ LIỆU MÔ PHỎNG'
    warnings = [w.value for w in at.warning]
    assert any("DỮ LIỆU MÔ PHỎNG" in w for w in warnings), "Expected 'DỮ LIỆU MÔ PHỎNG' warning before chat"

    # Submit a message on synth profile
    at.chat_input[0].set_value("Dư nợ ngắn hạn hiện tại là bao nhiêu?").run(timeout=35)
    assert not at.exception

    # After chat: warning banner must still contain 'DỮ LIỆU MÔ PHỎNG'
    warnings_post = [w.value for w in at.warning]
    assert any("DỮ LIỆU MÔ PHỎNG" in w for w in warnings_post), "Expected 'DỮ LIỆU MÔ PHỎNG' warning after chat"


def test_tc_t6_03_alert_center_ack_calls_post_ack_and_updates_status():
    """TC-T6-03: Navigating to Alert Center shows unacknowledged alert AL-002; clicking 'Đã xem' calls POST /v1/alerts/{id}/ack and updates status to 'Đã xác nhận'."""
    engine = get_app_engine(profile="real")
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id = 'AL-002'"))
        conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (rule_id, kpi_key, severity, message, value, threshold, is_acknowledged, created_at)
                VALUES ('AL-002', 'du_no_ngan_han', 'warning', 'Cảnh báo nợ vay ngắn hạn', 240000000000, 200000000000, false, now());
            """)
        )

    at = AppTest.from_file(APP_PATH)
    at.query_params["screen"] = "alerts"
    at.run(timeout=35)
    assert not at.exception

    # Alert AL-002 should have an ack button
    ack_buttons = [b for b in at.button if b.key and "ack_AL-002" in b.key]
    if not ack_buttons:
        ack_buttons = [b for b in at.button if "Đã xem" in b.label]
    assert len(ack_buttons) > 0, "Expected 'Đã xem' button for unacknowledged alert"

    # Click ack button
    ack_buttons[0].click().run(timeout=35)
    assert not at.exception

    # Status should now indicate confirmed
    combined_texts = " ".join([m.value for m in at.markdown] + [c.value for c in at.caption] + [s.value for s in at.success])
    assert "Đã xác nhận" in combined_texts, "Expected alert status updated to 'Đã xác nhận'"


def test_tc_t6_04_thumbs_down_feedback_persists_to_app_feedback_with_request_id():
    """TC-T6-04: Clicking 👎 + entering feedback note + submitting calls POST /v1/feedback and inserts row in app.feedback."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=35)
    assert not at.exception

    at.chat_input[0].set_value("Dư nợ ngắn hạn hiện tại là bao nhiêu?").run(timeout=35)
    assert not at.exception

    # Click thumbs down
    down_btns = [b for b in at.button if "👎" in b.label]
    assert len(down_btns) > 0, "Expected '👎' button in chat view"
    down_btns[0].click().run(timeout=35)
    assert not at.exception

    # Enter feedback note
    assert len(at.text_input) > 0 or len(at.text_area) > 0, "Expected feedback note text input"
    note_widget = at.text_input[0] if len(at.text_input) > 0 else at.text_area[0]
    note_widget.set_value("Cần chi tiết theo từng ngân hàng").run(timeout=35)

    # Submit feedback
    submit_btns = [b for b in at.button if "Gửi" in b.label or "Submit" in b.label]
    assert len(submit_btns) > 0, "Expected submit feedback button"
    submit_btns[0].click().run(timeout=35)
    assert not at.exception

    # Check database persistence
    engine = get_app_engine(profile="real")
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("""
                SELECT request_id, rating, note
                FROM app.feedback
                WHERE note = 'Cần chi tiết theo từng ngân hàng'
                ORDER BY created_at DESC
                LIMIT 1;
            """)
        ).fetchone()

    assert row is not None, "Feedback row must be inserted into app.feedback"
    assert row.rating == "down"
    assert row.note == "Cần chi tiết theo từng ngân hàng"
    assert row.request_id.startswith("req-")


def test_powerbi_quick_ask_query_params_preload_context():
    """Power BI Quick Ask integration: setting query params ?dashboard=...&kpi=... pre-populates Quick Ask banner/button."""
    at = AppTest.from_file(APP_PATH)
    at.query_params["dashboard"] = "tai_chinh"
    at.query_params["kpi"] = "du_no_ngan_han"
    at.run(timeout=35)
    assert not at.exception

    all_texts = " ".join([m.value for m in at.markdown] + [i.value for i in at.info] + [b.label for b in at.button])
    assert "Dư nợ ngắn hạn" in all_texts, "Expected Quick Ask context for 'Dư nợ ngắn hạn'"
