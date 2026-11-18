"""Integration and contract test suite for P4r API endpoints.

Specifications:
- Brief: task-1-brief.md
- Plan: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 1)
- GET /v1/kpi/{key}: byte-compatible without ?include
- GET /v1/kpi/{key}?include=series: returns series, delta_pct, previous_value, series_warning
- Strict RBAC: 403 on restricted role before cache
- Single audit log written per request
"""

import json
from pathlib import Path
import uuid
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.api.deps import reset_kpi_cache, reset_rate_limiter
from app.api.main import create_app
from app.core.config import Settings, get_settings
from db.apply_db import get_app_engine


@pytest.fixture(autouse=True)
def clean_singletons(monkeypatch: pytest.MonkeyPatch):
    """Reset rate limiter, cache singletons, and force offline mock LLM before each test."""
    monkeypatch.setenv("GOOGLE_API_KEY", "mock_offline")
    get_settings.cache_clear()
    reset_rate_limiter()
    reset_kpi_cache()
    yield
    reset_rate_limiter()
    reset_kpi_cache()
    get_settings.cache_clear()


@pytest.fixture
def client_ceo():
    app = create_app()
    return TestClient(app, headers={"Authorization": "Bearer gml-dev-token-ceo"})


@pytest.fixture
def client_ceo_synth():
    settings = Settings(data_profile="synth")
    app = create_app(settings=settings)
    return TestClient(app, headers={"Authorization": "Bearer gml-dev-token-ceo"})


@pytest.fixture
def client_kho():
    app = create_app()
    return TestClient(app, headers={"Authorization": "Bearer gml-dev-token-kho"})


def test_kpi_without_include_is_byte_compatible(client_ceo_synth):
    r = client_ceo_synth.get("/v1/kpi/du_no_ngan_han?profile=synth")
    assert r.status_code == 200
    body = r.json()
    assert body["series"] is None and body["delta_pct"] is None
    assert set(body) >= {
        "kpi_key",
        "kpi_name",
        "value",
        "unit",
        "as_of_date",
        "data_profile",
        "sql_executed",
        "warnings",
        "cached",
    }


def test_kpi_include_series_synth(client_ceo_synth):
    r = client_ceo_synth.get("/v1/kpi/du_no_ngan_han?profile=synth&include=series")
    assert r.status_code == 200
    b = r.json()
    assert b["series"] is not None
    assert len(b["series"]) <= 12 and b["series"][-1]["period"] == "2026-07"
    assert round(b["delta_pct"], 3) == -0.168  # 283,7 -> 236,07 (TC-T4-06)
    assert b["previous_value"] == pytest.approx(283700000000.0, rel=1e-4)
    assert "SYNTHETIC_DATA" in b["warnings"]


def test_kho_series_forbidden_before_cache(client_kho):
    assert client_kho.get("/v1/kpi/du_no_ngan_han?include=series").status_code == 403


def test_kpi_include_series_no_series_query(client_ceo_synth):
    r = client_ceo_synth.get("/v1/kpi/ltv_ratio?profile=synth&include=series")
    assert r.status_code == 200
    b = r.json()
    assert b["series"] is None
    assert b["previous_value"] is None
    assert b["delta_pct"] is None
    assert b["series_warning"] is None


def test_kpi_not_found_returns_404(client_ceo_synth):
    r = client_ceo_synth.get("/v1/kpi/non_existent_kpi")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "KPI_NOT_FOUND"


def test_kpi_invalid_include_returns_422(client_ceo_synth):
    r = client_ceo_synth.get("/v1/kpi/du_no_ngan_han?include=invalid_option")
    assert r.status_code == 422
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_kpi_series_writes_exactly_one_audit_log(client_ceo_synth):
    req_id = f"req-test-audit-series-{uuid.uuid4().hex[:8]}"
    r = client_ceo_synth.get(
        "/v1/kpi/du_no_ngan_han?profile=synth&include=series",
        headers={"X-Request-ID": req_id},
    )
    assert r.status_code == 200

    engine = get_app_engine(profile="synth")
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT user_id, role, query, request_id FROM app.audit_log WHERE request_id = :req_id"),
            {"req_id": req_id},
        ).fetchall()

    assert len(rows) == 1
    assert rows[0].role == "ceo"
    assert "du_no_ngan_han" in rows[0].query


@pytest.fixture
def client_ceo_synth_mock_llm(client_ceo_synth):
    return client_ceo_synth


@pytest.fixture
def seed_alert_with_evidence():
    engine = get_app_engine(profile="real")
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id LIKE 'TEST_%'"))
        # 1. Alert with evidence and domain (loan -> no_vay)
        conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (
                    rule_id, kpi_key, severity, message, value, threshold,
                    is_acknowledged, period, evidence, escalated_at, created_at
                )
                VALUES (
                    'TEST_AL', 'ty_le_su_dung_han_muc', 'critical',
                    'Tỷ lệ sử dụng hạn mức vượt ngưỡng 90%', 0.92, 0.90,
                    false, '2026-07',
                    '{"threshold_expr": ">= 0.90", "authority_role": "ceo"}'::jsonb,
                    '2026-07-31 10:00:00',
                    '2026-07-31 10:00:00'
                )
            """)
        )
        # 2. Alert for inventory (kho) - open, warning
        conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (
                    rule_id, kpi_key, severity, message, value, threshold,
                    is_acknowledged, period, evidence, created_at
                )
                VALUES (
                    'TEST_AL_KHO', 'gia_tri_hang_ton_kho', 'warning',
                    'Tồn kho tăng cao', 120000000000, 100000000000,
                    false, '2026-07',
                    '{"threshold_expr": ">= 100B"}'::jsonb,
                    '2026-07-31 08:00:00'
                )
            """)
        )
        # 3. Alert acked (for status filter test)
        conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (
                    rule_id, kpi_key, severity, message, value, threshold,
                    is_acknowledged, acknowledged_by, acknowledged_at, period, created_at
                )
                VALUES (
                    'TEST_AL_ACKED', 'ty_le_su_dung_han_muc', 'critical',
                    'Đã xử lý hạn mức', 0.91, 0.90,
                    true, 'usr_ceo', '2026-07-31 09:00:00', '2026-07',
                    '2026-07-30 10:00:00'
                )
            """)
        )
        # 4. Alert with unknown/uncatalogued kpi_key
        conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (
                    rule_id, kpi_key, severity, message, value, threshold,
                    is_acknowledged, period, created_at
                )
                VALUES (
                    'TEST_AL_UNKNOWN', 'uncatalogued_legacy_kpi', 'warning',
                    'Cảnh báo từ hệ thống cũ', 10, 5,
                    false, '2026-07',
                    '2026-07-29 10:00:00'
                )
            """)
        )
    yield
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id LIKE 'TEST_%'"))


def test_alerts_include_evidence_and_domain(seed_alert_with_evidence, client_ceo):
    res = client_ceo.get("/v1/alerts")
    assert res.status_code == 200
    alerts = res.json()["alerts"]
    a = next(x for x in alerts if x["rule_id"] == "TEST_AL")
    assert a["domain"] == "no_vay"
    assert a["evidence"] is not None
    assert a["evidence"]["threshold_expr"] == ">= 0.90"
    assert a["period"] == "2026-07"
    assert a["escalated_at"] is not None


def test_alerts_filters(seed_alert_with_evidence, client_ceo):
    # 1. Filter by domain
    kho_res = client_ceo.get("/v1/alerts?domain=kho")
    assert kho_res.status_code == 200
    kho_alerts = kho_res.json()["alerts"]
    assert len(kho_alerts) > 0
    assert all(x["domain"] == "kho" for x in kho_alerts)

    # 2. Filter by status: open
    open_res = client_ceo.get("/v1/alerts?status=open")
    assert open_res.status_code == 200
    open_alerts = open_res.json()["alerts"]
    assert len(open_alerts) > 0
    assert all(not x["is_acknowledged"] for x in open_alerts)

    # 3. Filter by status: acked
    acked_res = client_ceo.get("/v1/alerts?status=acked")
    assert acked_res.status_code == 200
    acked_alerts = acked_res.json()["alerts"]
    assert len(acked_alerts) > 0
    assert all(x["is_acknowledged"] for x in acked_alerts)

    # 4. Filter by severity
    crit_res = client_ceo.get("/v1/alerts?severity=critical")
    assert crit_res.status_code == 200
    crit_alerts = crit_res.json()["alerts"]
    assert len(crit_alerts) > 0
    assert all(x["severity"] in ("critical", "nghiem_trong") for x in crit_alerts)

    warn_res = client_ceo.get("/v1/alerts?severity=warning")
    assert warn_res.status_code == 200
    warn_alerts = warn_res.json()["alerts"]
    assert len(warn_alerts) > 0
    assert all(x["severity"] in ("warning", "canh_bao") for x in warn_alerts)

    # 5. Ordering: open before acked, critical before others, created_at DESC
    all_res = client_ceo.get("/v1/alerts")
    assert all_res.status_code == 200
    all_alerts = all_res.json()["alerts"]
    # Check open before acked
    seen_acked = False
    for item in all_alerts:
        if item["is_acknowledged"]:
            seen_acked = True
        else:
            assert not seen_acked, "Found open alert after acknowledged alert"

    # Among open alerts, critical should come before non-critical
    open_items = [x for x in all_alerts if not x["is_acknowledged"]]
    seen_non_critical = False
    for item in open_items:
        is_crit = item["severity"] in ("critical", "nghiem_trong")
        if not is_crit:
            seen_non_critical = True
        else:
            assert not seen_non_critical, "Found critical alert after non-critical open alert"


def test_alert_filters_do_not_bypass_rbac(seed_alert_with_evidence, client_kho):
    res = client_kho.get("/v1/alerts?domain=no_vay")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert len(data["alerts"]) == 0


def test_alerts_unknown_kpi_does_not_500(seed_alert_with_evidence, client_ceo):
    res = client_ceo.get("/v1/alerts")
    assert res.status_code == 200
    alerts = res.json()["alerts"]
    unk = next((x for x in alerts if x["rule_id"] == "TEST_AL_UNKNOWN"), None)
    assert unk is not None
    assert unk["domain"] is None


def test_chat_returns_kpi_keys(client_ceo_synth_mock_llm):
    res = client_ceo_synth_mock_llm.post("/v1/chat", json={"query": "Dư nợ ngắn hạn?"})
    assert res.status_code == 200
    data = res.json()
    assert "kpi_keys" in data
    assert "du_no_ngan_han" in data["kpi_keys"]


# ==============================================================================
# Task 3: /v1/actions Contract Tests
# ==============================================================================

@pytest.fixture
def client_ktt():
    app = create_app()
    return TestClient(app, headers={"Authorization": "Bearer gml-dev-token-ktt"})


@pytest.fixture
def approved_text_nt():
    return "Kích hoạt phương án khẩn cấp: ngừng toàn bộ các khoản giải ngân mới chưa cấp thiết."


@pytest.fixture
def approved_text_cb():
    return "Tạm dừng giải ngân mới từ các ngân hàng có tỷ lệ sử dụng trên 80%."


@pytest.fixture
def seed_alert_id(seed_alert_with_evidence):
    engine = get_app_engine(profile="real")
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id FROM app.alert_event WHERE rule_id = 'TEST_AL'")
        ).fetchone()
        return row.id


@pytest.fixture(autouse=True)
def clean_action_items_and_chat_turns():
    engine = get_app_engine(profile="real")
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.action_item"))
        conn.execute(sa.text("DELETE FROM app.chat_turn WHERE session_id LIKE 'test%' OR request_id LIKE 'req-chat-test%'"))
    yield
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.action_item"))
        conn.execute(sa.text("DELETE FROM app.chat_turn WHERE session_id LIKE 'test%' OR request_id LIKE 'req-chat-test%'"))


def audit_rows_for(request_id: str, profile: str = "real") -> int:
    engine = get_app_engine(profile=profile)
    with engine.connect() as conn:
        count = conn.execute(
            sa.text("SELECT count(*) FROM app.audit_log WHERE request_id = :rid"),
            {"rid": request_id},
        ).scalar()
        return int(count or 0)


def test_create_action_from_alert_assigns_authority_role(client_ceo, seed_alert_id, approved_text_nt):
    req_id = f"req-test-action-{uuid.uuid4().hex[:8]}"
    r = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": "   kích hoạt phương án khẩn cấp: ngừng toàn bộ các khoản giải ngân mới chưa cấp thiết.  ",
            "due_date": "2026-08-15",
            "note": "CEO phê duyệt khẩn cấp",
        },
        headers={"X-Request-ID": req_id},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["assigned_role"] == "ceo"
    assert body["status"] == "open"
    assert body["title"] == approved_text_nt
    assert body["domain"] == "no_vay"
    assert body["kpi_key"] == "ty_le_su_dung_han_muc"
    assert body["source_type"] == "alert"
    assert body["source_ref"] == str(seed_alert_id)
    assert body["due_date"] == "2026-08-15"
    assert body["note"] == "CEO phê duyệt khẩn cấp"
    assert body["created_by"] == "usr_ceo"
    assert "id" in body and isinstance(body["id"], int)
    assert audit_rows_for(req_id) == 1


def test_tc_t5_10_kho_cannot_create_finance_action(client_kho, seed_alert_id, approved_text_nt):
    req_id = f"req-test-kho-403-{uuid.uuid4().hex[:8]}"
    r = client_kho.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": approved_text_nt,
        },
        headers={"X-Request-ID": req_id},
    )
    assert r.status_code == 403
    body = r.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert audit_rows_for(req_id) == 1


def test_tc_t5_11_chat_source_of_other_user_is_404(client_ktt, client_ceo, approved_text_cb):
    # 1. Seed chat turn belonging to usr_ceo
    engine = get_app_engine(profile="real")
    ceo_req_id = f"req-chat-test-ceo-{uuid.uuid4().hex[:8]}"
    with engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO app.chat_turn (
                    session_id, user_id, query, kpi_keys, request_id
                ) VALUES (
                    'test-sess-ceo', 'usr_ceo', 'Tỷ lệ sử dụng hạn mức thế nào?',
                    ARRAY['ty_le_su_dung_han_muc'], :rid
                )
            """),
            {"rid": ceo_req_id},
        )

    # 2. client_ktt tries to create action referencing ceo's chat turn -> 404 SOURCE_NOT_FOUND
    req_id_ktt = f"req-test-ktt-chat-404-{uuid.uuid4().hex[:8]}"
    r = client_ktt.post(
        "/v1/actions",
        json={
            "source_type": "chat",
            "source_ref": ceo_req_id,
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "canh_bao",
            "title": approved_text_cb,
        },
        headers={"X-Request-ID": req_id_ktt},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "SOURCE_NOT_FOUND"
    assert audit_rows_for(req_id_ktt) == 1

    # 3. Happy path: client_ceo creates action referencing their own chat turn -> 201
    req_id_ceo = f"req-test-ceo-chat-201-{uuid.uuid4().hex[:8]}"
    r2 = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "chat",
            "source_ref": ceo_req_id,
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "canh_bao",
            "title": approved_text_cb,
        },
        headers={"X-Request-ID": req_id_ceo},
    )
    assert r2.status_code == 201
    assert r2.json()["source_ref"] == ceo_req_id
    assert r2.json()["assigned_role"] == "ke_toan_truong"
    assert audit_rows_for(req_id_ceo) == 1


def test_unknown_kpi_404_and_unapproved_title_422_and_duplicate_409(client_ceo, seed_alert_id, approved_text_nt):
    # a. Unknown KPI -> 404 KPI_NOT_FOUND (checked BEFORE can_access_kpi)
    req_unk = f"req-test-unk-kpi-{uuid.uuid4().hex[:8]}"
    r_unk = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "kpi_khong_ton_tai",
            "level": "nghiem_trong",
            "title": approved_text_nt,
        },
        headers={"X-Request-ID": req_unk},
    )
    assert r_unk.status_code == 404
    assert r_unk.json()["error"]["code"] == "KPI_NOT_FOUND"
    assert audit_rows_for(req_unk) == 1

    # b. Unapproved title -> 422 ACTION_NOT_APPROVED
    req_unapp = f"req-test-unapp-{uuid.uuid4().hex[:8]}"
    r_unapp = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": "Hành động tùy ý không có trong quy tắc nghiệp vụ",
        },
        headers={"X-Request-ID": req_unapp},
    )
    assert r_unapp.status_code == 422
    assert r_unapp.json()["error"]["code"] == "ACTION_NOT_APPROVED"
    assert audit_rows_for(req_unapp) == 1

    # c. Valid creation -> 201
    req_ok = f"req-test-dup-1-{uuid.uuid4().hex[:8]}"
    r_ok = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": approved_text_nt,
        },
        headers={"X-Request-ID": req_ok},
    )
    assert r_ok.status_code == 201
    assert audit_rows_for(req_ok) == 1

    # d. Duplicate creation -> 409 ACTION_DUPLICATE
    req_dup = f"req-test-dup-2-{uuid.uuid4().hex[:8]}"
    r_dup = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": approved_text_nt,
        },
        headers={"X-Request-ID": req_dup},
    )
    assert r_dup.status_code == 409
    assert r_dup.json()["error"]["code"] == "ACTION_DUPLICATE"
    assert audit_rows_for(req_dup) == 1


def test_list_and_patch_visibility(client_ceo, client_ktt, client_kho, seed_alert_id, approved_text_nt, approved_text_cb):
    # 1. Create Action A: CEO role, assigned_role="ceo", created_by="usr_ceo"
    r_a = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": approved_text_nt,
        },
    )
    assert r_a.status_code == 201
    act_a_id = r_a.json()["id"]

    # 2. GET /v1/actions visibility:
    # CEO sees Action A
    ceo_list = client_ceo.get("/v1/actions").json()["actions"]
    assert any(a["id"] == act_a_id for a in ceo_list)

    # KTT does NOT see Action A (assigned_role is ceo, created_by is ceo, and KTT is not ceo)
    ktt_list = client_ktt.get("/v1/actions").json()["actions"]
    assert not any(a["id"] == act_a_id for a in ktt_list)

    # Kho does NOT see Action A (cannot access ty_le_su_dung_han_muc)
    kho_list = client_kho.get("/v1/actions").json()["actions"]
    assert not any(a["id"] == act_a_id for a in kho_list)

    # 3. PATCH /v1/actions/{id}:
    # KTT patching Action A -> 404 ACTION_NOT_FOUND (does not leak existence)
    r_ktt_patch = client_ktt.patch(f"/v1/actions/{act_a_id}", json={"status": "in_progress"})
    assert r_ktt_patch.status_code == 404
    assert r_ktt_patch.json()["error"]["code"] == "ACTION_NOT_FOUND"

    # Kho patching Action A -> 404 ACTION_NOT_FOUND
    r_kho_patch = client_kho.patch(f"/v1/actions/{act_a_id}", json={"status": "in_progress"})
    assert r_kho_patch.status_code == 404
    assert r_kho_patch.json()["error"]["code"] == "ACTION_NOT_FOUND"

    # CEO patching Action A -> 200 OK
    r_ceo_patch = client_ceo.patch(
        f"/v1/actions/{act_a_id}",
        json={"status": "in_progress", "note": "Đang triển khai phương án khẩn cấp"},
    )
    assert r_ceo_patch.status_code == 200
    assert r_ceo_patch.json()["status"] == "in_progress"
    assert r_ceo_patch.json()["note"] == "Đang triển khai phương án khẩn cấp"

    # 4. Status filter test: GET /v1/actions?status=in_progress vs open
    r_in_prog = client_ceo.get("/v1/actions?status=in_progress")
    assert r_in_prog.status_code == 200
    assert any(a["id"] == act_a_id for a in r_in_prog.json()["actions"])

    r_open = client_ceo.get("/v1/actions?status=open")
    assert r_open.status_code == 200
    assert not any(a["id"] == act_a_id for a in r_open.json()["actions"])


def test_audit_has_no_title_or_note(client_ceo, seed_alert_id, approved_text_nt):
    unique_title_part = "phương án khẩn cấp"
    unique_note = "SECRET_MEMO_NOTE_9988"
    req_post_id = f"req-test-audit-post-{uuid.uuid4().hex[:8]}"
    req_patch_id = f"req-test-audit-patch-{uuid.uuid4().hex[:8]}"

    # POST action
    r_post = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": approved_text_nt,
            "note": unique_note,
        },
        headers={"X-Request-ID": req_post_id},
    )
    assert r_post.status_code == 201
    action_id = r_post.json()["id"]

    # PATCH action
    patch_note = "PATCH_SECRET_NOTE_7766"
    r_patch = client_ceo.patch(
        f"/v1/actions/{action_id}",
        json={"note": patch_note},
        headers={"X-Request-ID": req_patch_id},
    )
    assert r_patch.status_code == 200

    # Query audit logs for both requests
    engine = get_app_engine(profile="real")
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT request_id, query FROM app.audit_log WHERE request_id IN (:r1, :r2)"),
            {"r1": req_post_id, "r2": req_patch_id},
        ).fetchall()

    assert len(rows) == 2
    for row in rows:
        q = row.query or ""
        assert unique_note not in q
        assert patch_note not in q
        assert unique_title_part not in q
        assert approved_text_nt not in q


# ==============================================================================
# Task 4: /v1/pins Contract Tests
# ==============================================================================

@pytest.fixture(autouse=True)
def clean_pinned_kpis():
    """Ensure app.pinned_kpi is wiped in both real and synth profiles around each test."""
    for p in ("real", "synth"):
        eng = get_app_engine(profile=p)
        with eng.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.pinned_kpi"))
    yield
    for p in ("real", "synth"):
        eng = get_app_engine(profile=p)
        with eng.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.pinned_kpi"))


def test_pin_scoped_by_profile(client_ceo):
    # 1. Pin on real profile
    r_real = client_ceo.post("/v1/pins?profile=real", json={"kpi_key": "gia_tri_phai_tra"})
    assert r_real.status_code == 201
    assert "SYNTHETIC_DATA" not in r_real.json().get("warnings", [])

    # 2. Get pins on synth profile -> should not see real pin, warnings must have SYNTHETIC_DATA
    res_synth = client_ceo.get("/v1/pins?profile=synth")
    assert res_synth.status_code == 200
    synth_body = res_synth.json()
    assert [p["kpi_key"] for p in synth_body["pins"]] == []
    assert synth_body["total"] == 0
    assert "SYNTHETIC_DATA" in synth_body["warnings"]

    # 3. Pin on synth profile
    r_synth = client_ceo.post("/v1/pins?profile=synth", json={"kpi_key": "gia_tri_phai_tra"})
    assert r_synth.status_code == 201
    assert "SYNTHETIC_DATA" in r_synth.json()["warnings"]

    # 4. Verify synth pins now has the pin
    res_synth2 = client_ceo.get("/v1/pins?profile=synth")
    assert res_synth2.status_code == 200
    assert [p["kpi_key"] for p in res_synth2.json()["pins"]] == ["gia_tri_phai_tra"]
    assert "SYNTHETIC_DATA" in res_synth2.json()["warnings"]

    # 5. Verify real pins is intact and without SYNTHETIC_DATA
    res_real2 = client_ceo.get("/v1/pins?profile=real")
    assert res_real2.status_code == 200
    assert [p["kpi_key"] for p in res_real2.json()["pins"]] == ["gia_tri_phai_tra"]
    assert "SYNTHETIC_DATA" not in res_real2.json().get("warnings", [])


def test_pin_idempotent_and_forbidden(client_ceo, client_kho):
    req_1 = f"req-test-pin-1-{uuid.uuid4().hex[:8]}"
    req_2 = f"req-test-pin-2-{uuid.uuid4().hex[:8]}"
    req_forbid = f"req-test-pin-forbid-{uuid.uuid4().hex[:8]}"
    req_unk = f"req-test-pin-unk-{uuid.uuid4().hex[:8]}"

    # 1. First pin -> 201 Created
    r1 = client_ceo.post(
        "/v1/pins?profile=synth",
        json={"kpi_key": "gia_tri_phai_tra"},
        headers={"X-Request-ID": req_1},
    )
    assert r1.status_code == 201
    b1 = r1.json()
    assert b1["position"] == 1
    assert b1["kpi_key"] == "gia_tri_phai_tra"
    assert "created_at" in b1
    assert "SYNTHETIC_DATA" in b1["warnings"]
    assert audit_rows_for(req_1, profile="synth") == 1

    # 2. Second pin (same kpi_key) -> 200 OK (idempotent, same position and created_at)
    r2 = client_ceo.post(
        "/v1/pins?profile=synth",
        json={"kpi_key": "gia_tri_phai_tra"},
        headers={"X-Request-ID": req_2},
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["position"] == b1["position"]
    assert b2["created_at"] == b1["created_at"]
    assert b2["kpi_key"] == "gia_tri_phai_tra"
    assert "SYNTHETIC_DATA" in b2["warnings"]
    assert audit_rows_for(req_2, profile="synth") == 1

    # 3. Forbidden KPI for warehouse manager (kho cannot access finance KPI du_no_ngan_han)
    r_forbid = client_kho.post(
        "/v1/pins?profile=synth",
        json={"kpi_key": "du_no_ngan_han"},
        headers={"X-Request-ID": req_forbid},
    )
    assert r_forbid.status_code == 403
    assert r_forbid.json()["error"]["code"] == "FORBIDDEN"
    assert audit_rows_for(req_forbid, profile="synth") == 1

    # 4. Unknown KPI -> 404 KPI_NOT_FOUND (checked before can_access_kpi)
    r_unk = client_ceo.post(
        "/v1/pins?profile=synth",
        json={"kpi_key": "kpi_khong_ton_tai"},
        headers={"X-Request-ID": req_unk},
    )
    assert r_unk.status_code == 404
    assert r_unk.json()["error"]["code"] == "KPI_NOT_FOUND"
    assert audit_rows_for(req_unk, profile="synth") == 1


def test_delete_pin_and_ordering(client_ceo):
    kpis = ["gia_tri_phai_tra", "gia_tri_phai_thu", "ty_le_su_dung_han_muc"]

    # 1. Pin 3 KPIs in order on real profile
    for i, k in enumerate(kpis, start=1):
        res = client_ceo.post("/v1/pins?profile=real", json={"kpi_key": k})
        assert res.status_code == 201
        assert res.json()["position"] == i

    # 2. Check ordering on GET /v1/pins
    list_res = client_ceo.get("/v1/pins?profile=real")
    assert list_res.status_code == 200
    items = list_res.json()["pins"]
    assert [p["kpi_key"] for p in items] == kpis
    assert [p["position"] for p in items] == [1, 2, 3]

    # 3. Also pin kpis[1] on synth profile
    r_synth = client_ceo.post("/v1/pins?profile=synth", json={"kpi_key": kpis[1]})
    assert r_synth.status_code == 201

    # 4. DELETE kpis[1] on real -> returns deleted=1
    del_req_1 = f"req-test-del-1-{uuid.uuid4().hex[:8]}"
    del_res1 = client_ceo.delete(
        f"/v1/pins/{kpis[1]}?profile=real",
        headers={"X-Request-ID": del_req_1},
    )
    assert del_res1.status_code == 200
    assert del_res1.json()["deleted"] == 1
    assert "SYNTHETIC_DATA" not in del_res1.json().get("warnings", [])
    assert audit_rows_for(del_req_1, profile="real") == 1

    # 5. DELETE kpis[1] again on real -> returns deleted=0
    del_req_2 = f"req-test-del-2-{uuid.uuid4().hex[:8]}"
    del_res2 = client_ceo.delete(
        f"/v1/pins/{kpis[1]}?profile=real",
        headers={"X-Request-ID": del_req_2},
    )
    assert del_res2.status_code == 200
    assert del_res2.json()["deleted"] == 0
    assert audit_rows_for(del_req_2, profile="real") == 1

    # 6. Verify synth profile is unaffected
    synth_pins = client_ceo.get("/v1/pins?profile=synth").json()["pins"]
    assert [p["kpi_key"] for p in synth_pins] == [kpis[1]]

    # 7. Verify real profile now has remaining 2 pins in order
    real_pins = client_ceo.get("/v1/pins?profile=real").json()["pins"]
    assert [p["kpi_key"] for p in real_pins] == [kpis[0], kpis[2]]


def test_get_pins_filters_by_rbac(client_kho):
    # Directly seed pins in DB: one restricted (du_no_ngan_han) and one permitted (gia_tri_hang_ton_kho)
    engine = get_app_engine(profile="real")
    with engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO app.pinned_kpi (user_id, data_profile, kpi_key, position)
                VALUES
                    ('usr_kho', 'real', 'du_no_ngan_han', 1),
                    ('usr_kho', 'real', 'gia_tri_hang_ton_kho', 2)
            """)
        )

    # kho role should only see gia_tri_hang_ton_kho, du_no_ngan_han is filtered out by RBAC
    res = client_kho.get("/v1/pins?profile=real")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert len(body["pins"]) == 1
    assert body["pins"][0]["kpi_key"] == "gia_tri_hang_ton_kho"


# ==============================================================================
# Task 5: /v1/overview Contract Tests
# ==============================================================================

@pytest.fixture
def client_kho_synth():
    settings = Settings(data_profile="synth")
    app = create_app(settings=settings)
    return TestClient(app, headers={"Authorization": "Bearer gml-dev-token-kho"})


@pytest.fixture
def client_ktt_synth():
    settings = Settings(data_profile="synth")
    app = create_app(settings=settings)
    return TestClient(app, headers={"Authorization": "Bearer gml-dev-token-ktt"})


@pytest.fixture
def client_admin():
    app = create_app()
    return TestClient(app, headers={"Authorization": "Bearer gml-dev-token-admin"})


def test_tc_t5_12_one_failing_kpi_does_not_break_overview(monkeypatch, client_ceo_synth):
    import app.services.briefing as briefing_mod
    orig_val = briefing_mod.compute_kpi_value

    def fake_compute_val(key, *args, **kwargs):
        if key == "dong_tien_rong":
            raise briefing_mod.KpiComputationError("Simulated golden failure on dong_tien_rong")
        return orig_val(key, *args, **kwargs)

    monkeypatch.setattr(briefing_mod, "compute_kpi_value", fake_compute_val)

    r = client_ceo_synth.get("/v1/overview?profile=synth")
    assert r.status_code == 200
    b = r.json()
    card = next((c for c in b["kpis"] if c["kpi_key"] == "dong_tien_rong"), None)
    assert card is not None
    assert card["error"] is not None
    assert "Simulated golden failure" in card["error"]
    assert any(c["value"] is not None for c in b["kpis"] if c["kpi_key"] != "dong_tien_rong")

    # Critical #1: Non-failing KPI with series (du_no_ngan_han) must populate series, previous_value, delta_pct
    du_no_card = next((c for c in b["kpis"] if c["kpi_key"] == "du_no_ngan_han"), None)
    assert du_no_card is not None
    assert du_no_card["error"] is None
    assert len(du_no_card["series"]) > 0
    assert du_no_card["previous_value"] is not None
    assert du_no_card["delta_pct"] is not None


def test_overview_role_scoping(client_kho_synth):
    r = client_kho_synth.get("/v1/overview?profile=synth")
    assert r.status_code == 200
    b = r.json()
    assert [c["kpi_key"] for c in b["kpis"]] == [
        "gia_tri_hang_ton_kho",
        "so_luong_hang_ton_kho",
        "tong_ma_san_pham",
    ]
    assert all(a["domain"] == "kho" for a in b["top_alerts"])
    assert b["greeting_title"] == "Quản lý kho"


def test_overview_includes_pins_after_profile_kpis(client_ktt_synth):
    # KTT defaults: du_no_ngan_han, ty_le_su_dung_han_muc, tien_va_tuong_duong_tien, dong_tien_rong, gia_tri_phai_thu, gia_tri_phai_tra
    # Pin du_no_dai_han (valid for KTT, not in overview_kpis)
    # Pin du_no_ngan_han (already in overview_kpis)
    r1 = client_ktt_synth.post("/v1/pins?profile=synth", json={"kpi_key": "du_no_ngan_han"})
    assert r1.status_code in (200, 201)
    r2 = client_ktt_synth.post("/v1/pins?profile=synth", json={"kpi_key": "du_no_dai_han"})
    assert r2.status_code in (200, 201)

    r = client_ktt_synth.get("/v1/overview?profile=synth")
    assert r.status_code == 200
    b = r.json()
    kpi_keys = [c["kpi_key"] for c in b["kpis"]]

    # du_no_dai_han should be appended after the default 6 KPIs
    assert "du_no_dai_han" in kpi_keys
    assert kpi_keys[-1] == "du_no_dai_han"
    # du_no_ngan_han should not be duplicated
    assert kpi_keys.count("du_no_ngan_han") == 1

    # Check pinned flags
    card_dai_han = next(c for c in b["kpis"] if c["kpi_key"] == "du_no_dai_han")
    assert card_dai_han["pinned"] is True
    card_du_no = next(c for c in b["kpis"] if c["kpi_key"] == "du_no_ngan_han")
    assert card_du_no["pinned"] is True
    card_dong_tien = next(c for c in b["kpis"] if c["kpi_key"] == "dong_tien_rong")
    assert card_dong_tien["pinned"] is False


def test_overview_admin_empty_but_200(client_admin):
    r = client_admin.get("/v1/overview")
    assert r.status_code == 200
    b = r.json()
    assert b["kpis"] == []
    assert b["greeting_title"] == "Quản trị hệ thống"
    assert b["suggested_questions"] == []


def test_overview_audit_log_written_single_row(client_ceo_synth):
    req_id = f"req-test-overview-audit-{uuid.uuid4().hex[:8]}"
    r = client_ceo_synth.get("/v1/overview?profile=synth", headers={"X-Request-ID": req_id})
    assert r.status_code == 200

    engine = get_app_engine(profile="synth")
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT * FROM app.audit_log WHERE request_id = :req_id"),
            {"req_id": req_id},
        ).mappings().fetchall()

    assert len(rows) == 1
    row = rows[0]
    assert row["query"] == "GET /v1/overview"
    assert row["role"] == "ceo"
    assert row["user_id"] == "usr_ceo"
    assert row["views_accessed"] is not None
    assert len(row["views_accessed"]) > 0
    # Should contain ai_v_no_vay etc. from rendered cards
    assert "ai_v_no_vay" in row["views_accessed"]


# ==============================================================================
# Task 7: OpenAPI Snapshot Contract (M-13) & Audit Completeness (M-14)
# ==============================================================================

DOCS_OPENAPI_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "openapi.json"

NEW_ENDPOINTS = [
    ("GET", "/v1/overview"),
    ("GET", "/v1/actions"),
    ("POST", "/v1/actions"),
    ("PATCH", "/v1/actions/{action_id}"),
    ("GET", "/v1/pins"),
    ("POST", "/v1/pins"),
    ("DELETE", "/v1/pins/{kpi_key}"),
]


def test_m13_new_endpoints_in_openapi_snapshot():
    assert DOCS_OPENAPI_PATH.exists(), f"OpenAPI snapshot file {DOCS_OPENAPI_PATH} must exist"
    spec = json.loads(DOCS_OPENAPI_PATH.read_text(encoding="utf-8"))

    # 1. Verify 7 new endpoints exist in snapshot
    for m, p in NEW_ENDPOINTS:
        assert p in spec["paths"], f"Endpoint path {p} missing from openapi.json"
        assert m.lower() in spec["paths"][p], f"Method {m} missing from openapi.json for {p}"

    # 2. Verify ?include=series query param in /v1/kpi/{key}
    kpi_params = spec["paths"]["/v1/kpi/{key}"]["get"]["parameters"]
    include_param = next((p for p in kpi_params if p["name"] == "include"), None)
    assert include_param is not None, "Parameter ?include missing from /v1/kpi/{key}"

    # 3. Verify filters in /v1/alerts: domain, severity, status
    alert_params = spec["paths"]["/v1/alerts"]["get"]["parameters"]
    alert_param_names = {p["name"] for p in alert_params}
    for filter_name in ("domain", "severity", "status"):
        assert filter_name in alert_param_names, f"Filter ?{filter_name} missing from /v1/alerts"


def test_m14_every_new_endpoint_writes_one_audit_row(
    client_ceo, client_kho, client_ktt, seed_alert_id, approved_text_nt
):
    """M-14: Every new endpoint (200/201 as well as error paths 403/404/409/422) writes exactly one audit row.

    Verifies that no financial values, titles, or notes leak into the audit table.
    """
    cases = []

    # 1. GET /v1/overview -> 200
    rid = f"req-audit-ov-200-{uuid.uuid4().hex[:8]}"
    r = client_ceo.get("/v1/overview?profile=synth", headers={"X-Request-ID": rid})
    assert r.status_code == 200
    cases.append((rid, "synth", "GET /v1/overview"))

    # 2. GET /v1/actions -> 200
    rid = f"req-audit-act-get-200-{uuid.uuid4().hex[:8]}"
    r = client_ceo.get("/v1/actions", headers={"X-Request-ID": rid})
    assert r.status_code == 200
    cases.append((rid, "real", "GET /v1/actions"))

    # 3. POST /v1/actions -> 201 (Created)
    rid = f"req-audit-act-post-201-{uuid.uuid4().hex[:8]}"
    r = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": approved_text_nt,
            "note": "CEO audit test note",
        },
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 201
    act_id = r.json()["id"]
    cases.append((rid, "real", "POST /v1/actions"))

    # 4. POST /v1/actions -> 403 (Forbidden: kho creates finance action)
    rid = f"req-audit-act-post-403-{uuid.uuid4().hex[:8]}"
    r = client_kho.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": approved_text_nt,
        },
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 403
    cases.append((rid, "real", "POST /v1/actions"))

    # 5. POST /v1/actions -> 404 (Not Found: unknown kpi)
    rid = f"req-audit-act-post-404-{uuid.uuid4().hex[:8]}"
    r = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "kpi_unknown_nonexistent",
            "level": "nghiem_trong",
            "title": approved_text_nt,
        },
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 404
    cases.append((rid, "real", "POST /v1/actions"))

    # 6. POST /v1/actions -> 409 (Conflict: duplicate action)
    rid = f"req-audit-act-post-409-{uuid.uuid4().hex[:8]}"
    r = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": approved_text_nt,
        },
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 409
    cases.append((rid, "real", "POST /v1/actions"))

    # 7. POST /v1/actions -> 422 (Validation: unapproved title)
    rid = f"req-audit-act-post-422-{uuid.uuid4().hex[:8]}"
    r = client_ceo.post(
        "/v1/actions",
        json={
            "source_type": "alert",
            "source_ref": str(seed_alert_id),
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "nghiem_trong",
            "title": "Unapproved random title for audit test",
        },
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 422
    cases.append((rid, "real", "POST /v1/actions"))

    # 8. PATCH /v1/actions/{action_id} -> 200 (OK)
    rid = f"req-audit-act-patch-200-{uuid.uuid4().hex[:8]}"
    r = client_ceo.patch(
        f"/v1/actions/{act_id}",
        json={"status": "in_progress", "note": "Updating note"},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200
    cases.append((rid, "real", f"PATCH /v1/actions/{act_id}"))

    # 9. PATCH /v1/actions/{action_id} -> 404 (Not accessible by KTT)
    rid = f"req-audit-act-patch-404-{uuid.uuid4().hex[:8]}"
    r = client_ktt.patch(
        f"/v1/actions/{act_id}",
        json={"status": "in_progress"},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 404
    cases.append((rid, "real", f"PATCH /v1/actions/{act_id}"))

    # 10. GET /v1/pins -> 200
    rid = f"req-audit-pins-get-200-{uuid.uuid4().hex[:8]}"
    r = client_ceo.get("/v1/pins?profile=real", headers={"X-Request-ID": rid})
    assert r.status_code == 200
    cases.append((rid, "real", "GET /v1/pins"))

    # 11. POST /v1/pins -> 201 (Created)
    rid = f"req-audit-pins-post-201-{uuid.uuid4().hex[:8]}"
    r = client_ceo.post(
        "/v1/pins?profile=real",
        json={"kpi_key": "gia_tri_phai_tra"},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 201
    cases.append((rid, "real", "POST /v1/pins"))

    # 12. POST /v1/pins -> 200 (Idempotent OK)
    rid = f"req-audit-pins-post-200-{uuid.uuid4().hex[:8]}"
    r = client_ceo.post(
        "/v1/pins?profile=real",
        json={"kpi_key": "gia_tri_phai_tra"},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200
    cases.append((rid, "real", "POST /v1/pins"))

    # 13. POST /v1/pins -> 403 (Forbidden: kho pins du_no_ngan_han)
    rid = f"req-audit-pins-post-403-{uuid.uuid4().hex[:8]}"
    r = client_kho.post(
        "/v1/pins?profile=real",
        json={"kpi_key": "du_no_ngan_han"},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 403
    cases.append((rid, "real", "POST /v1/pins"))

    # 14. POST /v1/pins -> 404 (Not Found: unknown kpi)
    rid = f"req-audit-pins-post-404-{uuid.uuid4().hex[:8]}"
    r = client_ceo.post(
        "/v1/pins?profile=real",
        json={"kpi_key": "kpi_unknown_nonexistent"},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 404
    cases.append((rid, "real", "POST /v1/pins"))

    # 15. DELETE /v1/pins/{kpi_key} -> 200 (deleted=1)
    rid = f"req-audit-pins-del-1-{uuid.uuid4().hex[:8]}"
    r = client_ceo.delete(
        "/v1/pins/gia_tri_phai_tra?profile=real",
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200
    assert r.json()["deleted"] == 1
    cases.append((rid, "real", "DELETE /v1/pins/gia_tri_phai_tra"))

    # 16. DELETE /v1/pins/{kpi_key} -> 200 (deleted=0)
    rid = f"req-audit-pins-del-0-{uuid.uuid4().hex[:8]}"
    r = client_ceo.delete(
        "/v1/pins/gia_tri_phai_tra?profile=real",
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200
    assert r.json()["deleted"] == 0
    cases.append((rid, "real", "DELETE /v1/pins/gia_tri_phai_tra"))

    # 17. GET /v1/kpi/{key}?include=series -> 200
    rid = f"req-audit-kpi-series-200-{uuid.uuid4().hex[:8]}"
    r = client_ceo.get(
        "/v1/kpi/du_no_ngan_han?profile=real&include=series",
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200
    cases.append((rid, "real", "GET /v1/kpi/du_no_ngan_han?include=series"))

    # 18. GET /v1/alerts with filters -> 200
    rid = f"req-audit-alerts-200-{uuid.uuid4().hex[:8]}"
    r = client_ceo.get(
        "/v1/alerts?domain=no_vay&severity=critical&status=open",
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200
    cases.append((rid, "real", "GET /v1/alerts"))

    # Now verify M-14 audit rows for every single case
    for req_id, profile, expected_query_prefix in cases:
        eng = get_app_engine(profile=profile)
        with eng.connect() as conn:
            rows = conn.execute(
                sa.text("SELECT * FROM app.audit_log WHERE request_id = :rid"),
                {"rid": req_id},
            ).mappings().fetchall()

        assert len(rows) == 1, f"Expected exactly 1 audit row for {req_id} ({expected_query_prefix}), got {len(rows)}"
        row = rows[0]
        q = row["query"] or ""
        assert expected_query_prefix.split()[0] in q, f"HTTP method missing in query: {q}"
        # Ensure sensitive text / financial numbers are NOT logged
        assert "236065233815" not in q, f"Financial number leaked in audit query: {q}"
        assert "CEO audit test note" not in q, f"Note leaked in audit query: {q}"
        assert "Unapproved random title" not in q, f"Title leaked in audit query: {q}"


def test_alerts_non_dict_json_evidence_returns_none_cleanly(client_ceo):
    """Important #3: Non-dict JSON evidence (e.g. '[]') returns evidence=None without 500."""
    engine = get_app_engine(profile="real")
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id = 'TEST_AL_ARRAY_EV'"))
        row = conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (
                    rule_id, kpi_key, severity, message, value, threshold,
                    is_acknowledged, period, evidence, created_at
                )
                VALUES (
                    'TEST_AL_ARRAY_EV', 'du_no_ngan_han', 'warning',
                    'Non-dict JSON evidence test', 100.0, 50.0,
                    false, '2026-07', '[]'::jsonb, now()
                )
                RETURNING id;
            """)
        ).fetchone()
        alert_id = row[0]

    try:
        res = client_ceo.get("/v1/alerts")
        assert res.status_code == 200
        alerts = res.json()["alerts"]
        item = next((a for a in alerts if a["id"] == alert_id), None)
        assert item is not None
        assert item["evidence"] is None
    finally:
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.alert_event WHERE id = :aid"), {"aid": alert_id})


def test_invalid_profile_returns_422_across_routers(client_ceo):
    """Important #4: ?profile=invalid returns 422 VALIDATION_ERROR consistently across all routers."""
    endpoints = [
        ("GET", "/v1/overview?profile=invalid"),
        ("GET", "/v1/actions?profile=invalid"),
        ("POST", "/v1/actions?profile=invalid", {
            "source_type": "alert",
            "source_ref": "1",
            "kpi_key": "ty_le_su_dung_han_muc",
            "level": "canh_bao",
            "title": "Test",
        }),
        ("PATCH", "/v1/actions/1?profile=invalid", {"status": "done"}),
        ("GET", "/v1/alerts?profile=invalid"),
        ("POST", "/v1/alerts/1/ack?profile=invalid"),
        ("GET", "/v1/kpi/du_no_ngan_han?profile=invalid"),
        ("GET", "/v1/pins?profile=invalid"),
        ("POST", "/v1/pins?profile=invalid", {"kpi_key": "du_no_ngan_han"}),
        ("DELETE", "/v1/pins/du_no_ngan_han?profile=invalid"),
    ]
    for item in endpoints:
        method, url = item[0], item[1]
        body = item[2] if len(item) > 2 else None
        resp = client_ceo.request(method, url, json=body) if body is not None else client_ceo.request(method, url)
        assert resp.status_code == 422, f"Expected 422 for {method} {url}, got {resp.status_code}: {resp.text}"
        err = resp.json().get("error", {})
        assert err.get("code") == "VALIDATION_ERROR", f"Expected VALIDATION_ERROR for {method} {url}, got {err}"


def test_alerts_dedup_occurrence_count_and_group_ack(client_ceo):
    """GET /v1/alerts groups identical alerts with occurrence_count, ?dedup=false returns all, and ack resolves group."""
    engine = get_app_engine(profile="real")
    rule_id = "TEST_DEDUP_GROUP"
    created_ids: list[int] = []
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id = :rid"), {"rid": rule_id})
            for i in range(3):
                aid = conn.execute(
                    sa.text("""
                        INSERT INTO app.alert_event (
                            rule_id, kpi_key, severity, message, value, threshold,
                            is_acknowledged, period, created_at
                        )
                        VALUES (
                            :rid, 'ty_le_su_dung_han_muc', 'critical', :msg, :val, 0.90,
                            false, '2026-07', now() + (:offset * interval '1 second')
                        )
                        RETURNING id;
                    """),
                    {"rid": rule_id, "msg": f"Grouped alert #{i}", "val": 0.91 + 0.01 * i, "offset": i},
                ).scalar()
                created_ids.append(aid)

        # 1. Default dedup=true groups into 1 item with occurrence_count=3 and latest id
        res_dedup = client_ceo.get("/v1/alerts")
        assert res_dedup.status_code == 200
        grouped = [a for a in res_dedup.json()["alerts"] if a["rule_id"] == rule_id]
        assert len(grouped) == 1
        assert grouped[0]["occurrence_count"] == 3
        assert grouped[0]["id"] == created_ids[-1]

        # 2. ?dedup=false returns all 3 rows with occurrence_count=1
        res_raw = client_ceo.get("/v1/alerts?dedup=false")
        assert res_raw.status_code == 200
        ungrouped = [a for a in res_raw.json()["alerts"] if a["rule_id"] == rule_id]
        assert len(ungrouped) == 3
        assert all(a["occurrence_count"] == 1 for a in ungrouped)

        # 3. POST /v1/alerts/{latest_id}/ack acknowledges all 3 sibling open rows
        ack_res = client_ceo.post(f"/v1/alerts/{created_ids[-1]}/ack")
        assert ack_res.status_code == 200
        ack_body = ack_res.json()
        assert ack_body["id"] == created_ids[-1]
        assert ack_body["is_acknowledged"] is True

        # 4. No open alerts remain for this rule_id
        res_open = client_ceo.get("/v1/alerts?status=open")
        assert res_open.status_code == 200
        remaining_open = [a for a in res_open.json()["alerts"] if a["rule_id"] == rule_id]
        assert remaining_open == []

        # 5. Acked view groups all 3 acked alerts with occurrence_count=3
        res_acked = client_ceo.get("/v1/alerts?status=acked")
        assert res_acked.status_code == 200
        acked_grouped = [a for a in res_acked.json()["alerts"] if a["rule_id"] == rule_id]
        assert len(acked_grouped) == 1
        assert acked_grouped[0]["occurrence_count"] == 3
    finally:
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id = :rid"), {"rid": rule_id})





