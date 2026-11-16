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
