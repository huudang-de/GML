"""Unit tests for KPI service layer (Task 1 / P4r).

Specifications:
- Brief: task-1-brief.md
- Plan: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 1)
- compute_kpi_value: KPI exists -> RBAC -> cache -> golden query
- compute_kpi_series: KPI exists -> RBAC -> cache -> load_kpi_series -> summarize_series
- Cache isolation: f"{key}#series" key prevents collision with scalar KPI cache
- Exceptions: KpiForbidden (403), KpiNotFound (404), KpiComputationError (500)
"""

import pytest

from app.agents.models import SeriesSummary
from app.core.cache import ScopedTTLCache
from app.core.config import Settings
from app.services.kpi_service import (
    KpiComputationError,
    KpiForbidden,
    KpiNotFound,
    compute_kpi_series,
    compute_kpi_value,
)


@pytest.fixture
def cache():
    return ScopedTTLCache()


@pytest.fixture
def settings():
    return Settings(data_profile="synth")


def test_compute_kpi_value_success_and_cache(cache, settings):
    # 1. First execution: cache miss, runs golden query
    payload, sql, views, latency, cached = compute_kpi_value(
        key="du_no_ngan_han",
        role="ceo",
        profile="synth",
        settings=settings,
        cache=cache,
    )
    assert cached is False
    assert payload["kpi_key"] == "du_no_ngan_han"
    assert payload["value"] == pytest.approx(236070000000.0, rel=1e-4)
    assert "SYNTHETIC_DATA" in payload["warnings"]
    assert "ai_v_no_vay" in views
    assert sql != "[CACHE_HIT]"
    assert latency is not None

    # 2. Second execution: cache hit
    payload2, sql2, views2, latency2, cached2 = compute_kpi_value(
        key="du_no_ngan_han",
        role="ceo",
        profile="synth",
        settings=settings,
        cache=cache,
    )
    assert cached2 is True
    assert sql2 == "[CACHE_HIT]"
    assert payload2["cached"] is True
    assert payload2["value"] == payload["value"]


def test_compute_kpi_value_not_found(cache, settings):
    with pytest.raises(KpiNotFound) as exc_info:
        compute_kpi_value(
            key="kpi_khong_ton_tai",
            role="ceo",
            profile="synth",
            settings=settings,
            cache=cache,
        )
    assert "kpi_khong_ton_tai" in str(exc_info.value)


def test_compute_kpi_value_forbidden(cache, settings):
    with pytest.raises(KpiForbidden) as exc_info:
        compute_kpi_value(
            key="du_no_ngan_han",
            role="quan_ly_kho",
            profile="synth",
            settings=settings,
            cache=cache,
        )
    assert "quan_ly_kho" in str(exc_info.value)
    assert len(cache) == 0


def test_compute_kpi_series_success(cache, settings):
    summary = compute_kpi_series(
        key="du_no_ngan_han",
        role="ceo",
        profile="synth",
        settings=settings,
        cache=cache,
    )
    assert summary is not None
    assert isinstance(summary, SeriesSummary)
    assert len(summary.points) <= 12
    assert summary.points[-1].period == "2026-07"
    assert round(summary.delta_pct, 3) == -0.168

    # Second call should be a cache hit
    summary_cached = compute_kpi_series(
        key="du_no_ngan_han",
        role="ceo",
        profile="synth",
        settings=settings,
        cache=cache,
    )
    assert summary_cached is summary or summary_cached == summary


def test_compute_kpi_series_no_series_query(cache, settings):
    # ltv_ratio has no series query in knowledge
    summary = compute_kpi_series(
        key="ltv_ratio",
        role="ceo",
        profile="synth",
        settings=settings,
        cache=cache,
    )
    assert summary is None


def test_compute_kpi_series_forbidden(cache, settings):
    with pytest.raises(KpiForbidden):
        compute_kpi_series(
            key="du_no_ngan_han",
            role="quan_ly_kho",
            profile="synth",
            settings=settings,
            cache=cache,
        )
    assert len(cache) == 0


def test_series_cache_does_not_collide_with_value(cache, settings):
    # Calling value then series on the same key must yield 2 separate entries in cache
    compute_kpi_value("du_no_ngan_han", "ceo", "synth", settings, cache)
    assert len(cache) == 1

    compute_kpi_series("du_no_ngan_han", "ceo", "synth", settings, cache)
    assert len(cache) == 2

    # Check key formats
    val_key = cache.make_kpi_key("synth", "ceo", "du_no_ngan_han", str(settings.as_of_date))
    series_key = cache.make_kpi_key("synth", "ceo", "du_no_ngan_han#series", str(settings.as_of_date))

    val_entry = cache.get(val_key)
    series_entry = cache.get(series_key)

    assert isinstance(val_entry, dict)
    assert isinstance(series_entry, SeriesSummary)


# ==============================================================================
# Task 5: build_briefing Unit Tests
# ==============================================================================

from app.api.schemas import OverviewKpiCard, OverviewResponse
from app.core.auth import UserPrincipal
from app.services.briefing import build_briefing, row_to_alert_item
from db.apply_db import get_app_engine
import sqlalchemy as sa


def test_build_briefing_direct_structure_and_counts(cache, settings):
    user = UserPrincipal(user_id="usr_ceo", role="ceo", display_name="Nguyễn Văn A (CEO)")
    app_engine = get_app_engine(profile="synth")

    resp = build_briefing(user=user, profile="synth", settings=settings, cache=cache, app_engine=app_engine)

    assert isinstance(resp, OverviewResponse)
    assert resp.greeting_title == "Tổng Giám đốc"
    assert resp.data_profile == "synth"
    assert resp.as_of_date == str(settings.as_of_date)
    assert "SYNTHETIC_DATA" in resp.warnings
    assert isinstance(resp.open_alerts, dict)
    assert "nghiem_trong" in resp.open_alerts
    assert "canh_bao" in resp.open_alerts
    assert isinstance(resp.open_actions, int)
    assert len(resp.kpis) > 0
    assert len(resp.suggested_questions) > 0
    # Every card must be an OverviewKpiCard
    for c in resp.kpis:
        assert isinstance(c, OverviewKpiCard)
        assert c.domain is not None

    # Critical #1 regression guard: series, previous_value, and delta_pct must be populated
    du_no_card = next((c for c in resp.kpis if c.kpi_key == "du_no_ngan_han"), None)
    assert du_no_card is not None
    assert du_no_card.error is None
    assert len(du_no_card.series) > 0
    assert du_no_card.previous_value is not None
    assert du_no_card.delta_pct is not None


def test_build_briefing_one_failing_kpi_isolated(cache, settings, monkeypatch):
    import app.services.briefing as briefing_mod
    orig_val = briefing_mod.compute_kpi_value

    def fake_compute_val(key, *args, **kwargs):
        if key == "dong_tien_rong":
            raise KpiComputationError("Simulated query timeout on dong_tien_rong")
        return orig_val(key, *args, **kwargs)

    monkeypatch.setattr(briefing_mod, "compute_kpi_value", fake_compute_val)

    user = UserPrincipal(user_id="usr_ceo", role="ceo", display_name="CEO")
    app_engine = get_app_engine(profile="synth")

    resp = briefing_mod.build_briefing(user=user, profile="synth", settings=settings, cache=cache, app_engine=app_engine)

    failed_card = next((c for c in resp.kpis if c.kpi_key == "dong_tien_rong"), None)
    assert failed_card is not None
    assert failed_card.value is None
    assert "Simulated query timeout" in (failed_card.error or "")
    assert failed_card.kpi_name is not None  # metadata preserved from get_kpi

    # Other cards must succeed
    other_cards = [c for c in resp.kpis if c.kpi_key != "dong_tien_rong"]
    assert len(other_cards) > 0
    assert any(c.value is not None for c in other_cards)
    assert all(c.error is None for c in other_cards)


def test_build_briefing_uncatalogued_alert_safety(cache, settings):
    app_engine = get_app_engine(profile="synth")
    # Seed an uncatalogued alert
    with app_engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO app.alert_event (rule_id, kpi_key, severity, message, value, threshold, is_acknowledged, created_at)
                VALUES ('TEST_UNCAT', 'uncatalogued_metric_999', 'nghiem_trong', 'Uncatalogued metric alert', 99.0, 50.0, FALSE, now());
            """)
        )

    user = UserPrincipal(user_id="usr_ceo", role="ceo", display_name="CEO")
    # Must not raise KeyError or crash
    resp = build_briefing(user=user, profile="synth", settings=settings, cache=cache, app_engine=app_engine)
    assert isinstance(resp, OverviewResponse)
    assert resp.open_alerts["nghiem_trong"] >= 1


def test_row_to_alert_item_handles_non_dict_json_evidence():
    from types import SimpleNamespace
    from datetime import datetime, timezone

    row = SimpleNamespace(
        id=999,
        rule_id="AL-NONDICT",
        kpi_key="du_no_ngan_han",
        severity="warning",
        message="Test non-dict evidence",
        value=10.0,
        threshold=5.0,
        is_acknowledged=False,
        acknowledged_by=None,
        acknowledged_at=None,
        created_at=datetime.now(timezone.utc),
        period="2026-07",
        evidence="[]",
        escalated_at=None,
    )
    item = row_to_alert_item(row)
    assert item.evidence is None
    assert item.domain == "no_vay"
    assert item.occurrence_count == 1


def test_build_briefing_deduplicates_open_alerts(cache, settings):
    """Repeated unacknowledged alerts with same (rule_id, kpi_key, severity) are grouped in build_briefing."""
    app_engine = get_app_engine(profile="synth")
    rule_id = "TEST_DEDUP_BRIEFING"
    inserted_ids: list[int] = []
    try:
        with app_engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id = :rid"), {"rid": rule_id})
            for i in range(3):
                aid = conn.execute(
                    sa.text("""
                        INSERT INTO app.alert_event (
                            rule_id, kpi_key, severity, message, value, threshold, is_acknowledged, created_at
                        )
                        VALUES (
                            :rid, 'du_no_ngan_han', 'nghiem_trong', :msg, :val, 200.0, FALSE,
                            now() + (:offset * interval '1 second')
                        )
                        RETURNING id;
                    """),
                    {"rid": rule_id, "msg": f"Alert #{i}", "val": 210.0 + i, "offset": i},
                ).scalar()
                inserted_ids.append(aid)

        # Also clean other TEST_UNCAT duplicates if any, or check delta by ensuring baseline is consistent
        user = UserPrincipal(user_id="usr_ceo", role="ceo", display_name="CEO")
        resp = build_briefing(user=user, profile="synth", settings=settings, cache=cache, app_engine=app_engine)

        matching_top = [a for a in resp.top_alerts if a.rule_id == rule_id]
        assert len(matching_top) == 1
        assert matching_top[0].occurrence_count == 3
        assert matching_top[0].id == inserted_ids[-1]
    finally:
        with app_engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id = :rid"), {"rid": rule_id})


def test_gemini_clients_pass_fast_fail_timeout_and_fallback(monkeypatch):
    """GeminiTextLLMClient & GeminiSqlLLMClient pass timeout=12.0, max_retries=1 and fall back cleanly."""
    from types import SimpleNamespace
    from datetime import date
    import langchain_google_genai
    from app.agents.llm_text import GeminiTextLLMClient
    from app.sql.context import SqlPromptContext
    from app.sql.generator import GeminiSqlLLMClient

    captured_kwargs: list[dict] = []

    class HangingChatGemini:
        def __init__(self, **kwargs):
            captured_kwargs.append(kwargs)

        def invoke(self, _messages):
            raise TimeoutError("Simulated Gemini API timeout")

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", HangingChatGemini)

    cfg = Settings(google_api_key="test-key-12345678901234567890", llm_model="gemini-2.5-flash")

    text_client = GeminiTextLLMClient(settings=cfg)
    text_out = text_client.generate_text("sys", "KPI: du_no_ngan_han\nValue: 236 tỷ")
    assert "KPI: du_no_ngan_han" in text_out

    sql_client = GeminiSqlLLMClient(settings=cfg)
    ctx = SqlPromptContext(
        question="Dư nợ ngắn hạn?",
        role="ceo",
        data_profile="synth",
        as_of_date=date(2026, 7, 31),
        allowed_views={"ai_v_no_vay"},
        catalog_markdown="- ai_v_no_vay",
        c1_caveats=[],
        golden_matches=[],
    )
    drafts = sql_client.generate_candidates(ctx, n=1)
    assert len(drafts) == 1
    repaired = sql_client.repair_sql(ctx, "SELECT * FROM silver.tbl;", "invalid schema")
    assert "ai_views." in repaired

    assert len(captured_kwargs) == 3
    for kw in captured_kwargs:
        assert kw.get("timeout") == 12.0
        assert kw.get("max_retries") == 1


