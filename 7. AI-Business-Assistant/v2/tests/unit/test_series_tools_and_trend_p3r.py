"""Unit tests for P3r: Series Tools, TrendAnalyst Knowledge Integration, and Alert Evidence.

Specifications:
- Spec §5 T3 (TrendAnalyst & DecisionAdvisor Revision)
- TC-T3-14: No fake series fallback for KPIs without time-series queries
- TC-T3-15: Canonical series loading from T2 knowledge layer
- RBAC enforcement on time-series query loading
"""

from unittest.mock import MagicMock
import pytest
from sqlalchemy.engine import Engine

from app.agents.models import TrendPoint
from app.agents.trend_agent import analyze_kpi_trend, load_kpi_series
from app.knowledge.models import SeriesQuery
from app.sql.executor import SqlExecutionResult


@pytest.fixture
def executed_sql():
    return []


@pytest.fixture
def fake_engine(monkeypatch, executed_sql):
    fake_eng = MagicMock(spec=Engine)

    def mock_execute(sql: str, engine: Engine | None = None, **kwargs):
        executed_sql.append(sql)
        return SqlExecutionResult(
            sql=sql,
            status="ok",
            rows=[
                {"period": f"2026-{m:02d}", "value": 100.0 + m}
                for m in range(1, 13)
            ],
            columns=["period", "value"],
            row_count=12,
            latency_ms=1.0,
        )

    monkeypatch.setattr("app.agents.trend_agent.execute_validated_sql", mock_execute)
    return fake_eng


# ==============================================================================
# Task 1: TC-T3-14 & TC-T3-15: Series Loading from T2 & No Fake Fallback
# ==============================================================================


def test_tc_t3_14_kpi_without_series_ref_has_no_fake_series(fake_engine, executed_sql):
    """TC-T3-14:
    
    When a valid KPI has no series_ref in knowledge base (e.g. ltv_ratio),
    TrendAnalyst returns error 'KPI 'ltv_ratio' chưa có truy vấn chuỗi thời gian'
    and does NOT execute or return the fake '0.0 AS value' single-month series.
    """
    trend, warnings, err = analyze_kpi_trend("ltv_ratio", role="ceo", data_profile="synth", engine=fake_engine)
    assert trend is None
    assert err is not None
    assert "chưa có truy vấn chuỗi thời gian" in err
    assert not any("0.0 AS value" in s for s in executed_sql)


def test_load_kpi_series_uses_knowledge_sql(monkeypatch, fake_engine, executed_sql):
    """TC-T3-15:
    
    load_kpi_series retrieves time-series SQL from T2 get_series_query.
    """
    test_sq = SeriesQuery(
        id="S_test_custom",
        kpi_key="du_no_ngan_han",
        sql_file="test.sql",
        sql_text="""
        SELECT to_char(posting_date, 'YYYY-MM') AS period, SUM(credit_balance) AS value
        FROM ai_views.ai_v_no_vay /*S_TEST*/
        WHERE record_type = 'ledger_balance'
        GROUP BY 1 ORDER BY 1;
        """,
        views_used=["ai_v_no_vay"],
    )
    monkeypatch.setattr("app.agents.trend_agent.get_series_query", lambda kpi: test_sq if kpi == "du_no_ngan_han" else None)

    series, sql, err = load_kpi_series("du_no_ngan_han", role="ceo", data_profile="synth", engine=fake_engine)
    assert err is None
    assert sql is not None
    assert "S_TEST" in sql
    assert any("S_TEST" in s for s in executed_sql)
    assert len(series) == 12
    assert series[0].period == "2026-01"


def test_load_kpi_series_rbac_rejects_kho_on_debt(fake_engine):
    """RBAC security: quan_ly_kho cannot access ai_v_no_vay for du_no_ngan_han."""
    series, sql, err = load_kpi_series("du_no_ngan_han", role="quan_ly_kho", data_profile="synth", engine=fake_engine)
    assert series == []
    assert sql is None
    assert err is not None
    assert "quyền" in err.lower()


def test_load_kpi_series_non_kpi_fallback_ton_kho_sku(fake_engine, executed_sql):
    """_NON_KPI_SERIES_SQL correctly handles ton_kho_sku parameterized by product_code."""
    series, sql, err = load_kpi_series("ton_kho_sku", role="ceo", data_profile="synth", engine=fake_engine, product_code="TEST_SKU_01")
    assert err is None
    assert sql is not None
    assert "TEST_SKU_01" in sql
    assert any("TEST_SKU_01" in s for s in executed_sql)


def test_load_kpi_series_non_kpi_fallback_current_ratio(fake_engine, executed_sql):
    """_NON_KPI_SERIES_SQL correctly handles current_ratio."""
    series, sql, err = load_kpi_series("current_ratio", role="ceo", data_profile="synth", engine=fake_engine)
    assert err is None
    assert sql is not None
    assert "B01-DN_100" in sql
