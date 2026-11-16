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

