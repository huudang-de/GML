"""Integration and contract test suite for P4r API endpoints.

Specifications:
- Brief: task-1-brief.md
- Plan: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 1)
- GET /v1/kpi/{key}: byte-compatible without ?include
- GET /v1/kpi/{key}?include=series: returns series, delta_pct, previous_value, series_warning
- Strict RBAC: 403 on restricted role before cache
- Single audit log written per request
"""

import uuid
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.api.deps import reset_kpi_cache, reset_rate_limiter
from app.api.main import create_app
from app.core.config import Settings
from db.apply_db import get_app_engine


@pytest.fixture(autouse=True)
def clean_singletons():
    """Reset rate limiter and cache singletons before each test."""
    reset_rate_limiter()
    reset_kpi_cache()
    yield
    reset_rate_limiter()
    reset_kpi_cache()


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

