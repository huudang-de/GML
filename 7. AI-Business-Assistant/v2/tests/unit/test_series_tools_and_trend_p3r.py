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

from app.agents.advisor import resolve_approved_action
from app.agents.models import AlertEvidence, SeriesSummary, Trend, TrendAnomaly, TrendPoint
from app.agents.series_tools import build_alert_evidence, summarize_series
from app.agents.trend_agent import analyze_kpi_trend, load_kpi_series
from app.knowledge.loader import get_business_actions
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


# ==============================================================================
# Task 2: summarize_series & build_alert_evidence (TC-T3-15)
# ==============================================================================

P = lambda p, v: TrendPoint(period=p, value=v)


def test_summarize_series_delta():
    s = summarize_series([P("2026-06", 283.7), P("2026-07", 236.07)])
    assert s.last_value == 236.07 and s.previous_value == 283.7
    assert round(s.delta_pct, 3) == -0.168


def test_summarize_series_single_point_and_zero_prev():
    assert summarize_series([P("2026-07", 5.0)]).delta_pct is None
    assert summarize_series([P("2026-06", 0.0), P("2026-07", 5.0)]).delta_pct is None
    assert summarize_series([]).delta_pct is None
    assert summarize_series([]).last_value is None


def test_tc_t3_15_evidence_numbers_grounded():
    trend = Trend(
        kpi_key="ty_le_su_dung_han_muc",
        data_coverage=12,
        series=[P(f"2025-{m:02d}", 0.5) for m in range(8, 13)] + [P(f"2026-{m:02d}", 0.6 + m / 100) for m in range(1, 8)],
        source_query_id="t",
    )
    ev = build_alert_evidence("ty_le_su_dung_han_muc", "nghiem_trong", 0.92, trend)
    allowed = {p.value for p in trend.series} | {0.92, 0.90}
    numbers = [p.value for p in ev.series] + [ev.value]
    assert all(n in allowed for n in numbers)
    assert ev.threshold_expr == ">= 0.90" and ev.authority_role == "ceo"
    assert len(ev.series) == 12 and ev.period == "2026-07"


def test_evidence_without_trend():
    ev = build_alert_evidence("dong_tien_rong", "canh_bao", -1.0, None)
    assert ev.series == [] and ev.coverage_warning == "Không có dữ liệu chuỗi"
    assert ev.period is None
    assert ev.anomalies == []


def test_evidence_short_coverage_warning_and_anomalies_filtered():
    trend = Trend(
        kpi_key="ty_le_su_dung_han_muc",
        data_coverage=4,
        series=[P("2026-01", 0.5), P("2026-02", 0.6), P("2026-03", 0.7), P("2026-04", 0.75)],
        anomalies=[
            TrendAnomaly(period="2026-01", value=0.5, severity="canh_bao", reason="Spike"),
            TrendAnomaly(period="2026-04", value=0.75, severity="canh_bao", reason="High usage"),
        ],
        source_query_id="t",
    )
    # limit=2 means only 2026-03 and 2026-04 will be in series; 2026-01 anomaly must be filtered out
    ev = build_alert_evidence("ty_le_su_dung_han_muc", "canh_bao", 0.75, trend, limit=2)
    assert ev.coverage_warning == "Chỉ có 4 tháng dữ liệu, chưa đủ để phân tích xu hướng"
    assert len(ev.series) == 2
    assert [p.period for p in ev.series] == ["2026-03", "2026-04"]
    assert len(ev.anomalies) == 1
    assert ev.anomalies[0].period == "2026-04"
    assert ev.threshold_expr == ">= 0.70"
    assert ev.period == "2026-04"


# ==============================================================================
# Task 3: resolve_approved_action (TC-T3-11)
# ==============================================================================


def test_resolve_approved_action_exact_and_normalized():
    acts = get_business_actions("ty_le_su_dung_han_muc", "canh_bao")["actions"]
    assert resolve_approved_action("ty_le_su_dung_han_muc", "canh_bao", "  " + acts[0].upper() + " ") == (acts[0], "ke_toan_truong")


def test_resolve_approved_action_rejects_near_miss_and_unknown():
    acts = get_business_actions("ty_le_su_dung_han_muc", "canh_bao")["actions"]
    assert resolve_approved_action("ty_le_su_dung_han_muc", "canh_bao", acts[0] + " ngay") is None
    assert resolve_approved_action("ty_le_su_dung_han_muc", "canh_bao", "Bán bớt tài sản") is None
    assert resolve_approved_action("du_no_ngan_han", "canh_bao", acts[0]) is None
    assert resolve_approved_action("ty_le_su_dung_han_muc", "canh_bao", "") is None
    assert resolve_approved_action("ty_le_su_dung_han_muc", "canh_bao", "   ") is None
    assert resolve_approved_action("unknown_kpi", "canh_bao", acts[0]) is None
    assert resolve_approved_action("ty_le_su_dung_han_muc", "unknown_level", acts[0]) is None


# ==============================================================================
# Task 4: Final Review Fix Wave Coverage (Normalizations, Invariants, Safe Fallbacks)
# ==============================================================================


def test_build_alert_evidence_severity_alias_normalization_and_validation():
    """Important #1: build_alert_evidence normalizes warning->canh_bao, critical->nghiem_trong,
    and raises ValueError on unknown level.
    """
    trend = Trend(
        kpi_key="ty_le_su_dung_han_muc",
        data_coverage=12,
        series=[P(f"2026-{m:02d}", 0.5) for m in range(1, 13)],
        source_query_id="t",
    )
    # "warning" alias -> normalized to "canh_bao"
    ev_warn = build_alert_evidence("ty_le_su_dung_han_muc", "warning", 0.75, trend)
    assert ev_warn.level == "canh_bao"
    assert ev_warn.threshold_expr == ">= 0.70"
    assert len(ev_warn.approved_actions) > 0
    assert ev_warn.authority_role == "ke_toan_truong"

    # "critical" alias -> normalized to "nghiem_trong"
    ev_crit = build_alert_evidence("ty_le_su_dung_han_muc", "critical", 0.95, trend)
    assert ev_crit.level == "nghiem_trong"
    assert ev_crit.threshold_expr == ">= 0.90"
    assert len(ev_crit.approved_actions) > 0
    assert ev_crit.authority_role == "ceo"

    # Unknown level raises ValueError
    with pytest.raises(ValueError, match="Unsupported alert level"):
        build_alert_evidence("ty_le_su_dung_han_muc", "info", 0.5, trend)


def test_build_alert_evidence_zero_limit_coverage_warning_invariant():
    """Important #2: build_alert_evidence with limit=0 on a 12-month trend sets series=[]
    and non-empty coverage_warning ('Không có dữ liệu chuỗi').
    """
    trend = Trend(
        kpi_key="ty_le_su_dung_han_muc",
        data_coverage=12,
        series=[P(f"2026-{m:02d}", 0.5) for m in range(1, 13)],
        source_query_id="t",
    )
    ev = build_alert_evidence("ty_le_su_dung_han_muc", "canh_bao", 0.75, trend, limit=0)
    assert ev.series == []
    assert ev.coverage_warning == "Không có dữ liệu chuỗi"
    assert ev.period is None
    assert ev.anomalies == []


def test_build_alert_evidence_missing_nguong_and_rules_safe_fallback():
    """Minor #3: build_alert_evidence on a KPI missing nguong / business_rules
    safely sets threshold_expr=None, approved_actions=[], authority_role=None.
    """
    trend = Trend(
        kpi_key="du_no_ngan_han",
        data_coverage=12,
        series=[P(f"2026-{m:02d}", 100.0) for m in range(1, 13)],
        source_query_id="t",
    )
    ev = build_alert_evidence("du_no_ngan_han", "canh_bao", 120.0, trend)
    assert ev.threshold_expr is None
    assert ev.approved_actions == []
    assert ev.authority_role is None
    assert len(ev.series) == 12


def test_summarize_series_limit_non_positive_and_negative_previous_value():
    """Minor #3: summarize_series with limit <= 0 returns empty points, and negative
    previous_value uses abs(previous_value) for delta_pct.
    """
    pts = [P("2026-01", 100.0), P("2026-02", 110.0)]
    s_zero = summarize_series(pts, limit=0)
    assert s_zero.points == []
    assert s_zero.last_value is None
    assert s_zero.previous_value is None
    assert s_zero.delta_pct is None

    s_neg_limit = summarize_series(pts, limit=-5)
    assert s_neg_limit.points == []
    assert s_neg_limit.last_value is None
    assert s_neg_limit.delta_pct is None

    # Negative previous_value: delta = (-50 - (-100)) / abs(-100) = +0.50
    neg_prev_pts = [P("2026-01", -100.0), P("2026-02", -50.0)]
    s_neg_val = summarize_series(neg_prev_pts)
    assert s_neg_val.last_value == -50.0
    assert s_neg_val.previous_value == -100.0
    assert s_neg_val.delta_pct == 0.50

    # Negative to more negative: delta = (-150 - (-100)) / abs(-100) = -0.50
    neg_prev_pts2 = [P("2026-01", -100.0), P("2026-02", -150.0)]
    s_neg_val2 = summarize_series(neg_prev_pts2)
    assert s_neg_val2.delta_pct == -0.50


def test_load_kpi_series_error_propagation_and_chronological_sorting(monkeypatch, fake_engine):
    """Minor #3: load_kpi_series propagates exec_res.error and sorts out-of-order rows chronologically."""
    # 1. Error propagation
    def mock_execute_err(sql: str, engine: Engine | None = None, **kwargs):
        return SqlExecutionResult(
            sql=sql,
            status="execution_error",
            error="DB error: connection lost",
            rows=[],
            columns=[],
            row_count=0,
            latency_ms=0.5,
        )

    monkeypatch.setattr("app.agents.trend_agent.execute_validated_sql", mock_execute_err)
    series_err, sql_err, err_msg = load_kpi_series("ty_le_su_dung_han_muc", role="ceo", engine=fake_engine)
    assert series_err == []
    assert sql_err is None
    assert err_msg == "Lỗi truy vấn SQL: DB error: connection lost"

    # 2. Chronological sorting of out-of-order rows
    def mock_execute_unordered(sql: str, engine: Engine | None = None, **kwargs):
        return SqlExecutionResult(
            sql=sql,
            status="ok",
            rows=[
                {"period": "2026-05", "value": 50.0},
                {"period": "2026-01", "value": 10.0},
                {"period": "2026-03", "value": 30.0},
            ],
            columns=["period", "value"],
            row_count=3,
            latency_ms=0.5,
        )

    monkeypatch.setattr("app.agents.trend_agent.execute_validated_sql", mock_execute_unordered)
    series_sorted, sql_sorted, err_sorted = load_kpi_series("ty_le_su_dung_han_muc", role="ceo", engine=fake_engine)
    assert err_sorted is None
    assert [p.period for p in series_sorted] == ["2026-01", "2026-03", "2026-05"]
    assert [p.value for p in series_sorted] == [10.0, 30.0, 50.0]



