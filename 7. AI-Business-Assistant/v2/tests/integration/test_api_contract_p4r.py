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
