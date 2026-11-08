"""Integration tests for Task 3: TrendAnalyst and Database Execution on Real & Synthetic Profiles.

Specifications:
- TC-T3-09: Detect labeled synthetic anomalies with >= 90% recall and <= 1 false positive per KPI
- TC-T3-10: Honest data coverage when real revenue has only 1 month (no fabricated MoM/YoY growth)
- Security: Role-based view access check blocks unauthorized trend analysis
"""

from pathlib import Path
import pytest
import yaml

from app.agents.trend_agent import analyze_kpi_trend
from db.apply_db import get_ro_engine

ANOMALIES_YAML = Path(__file__).resolve().parent.parent.parent / "db" / "synthetic" / "anomalies.yaml"


def test_tc_t3_09_trend_detects_synthetic_anomalies_on_gml_synth():
    """TC-T3-09 & M-09 (>= 90% recall) & M-10 (<= 1 false positive per KPI):

    1. du_no_ngan_han on synth:
       - data_coverage == 12
       - abs(trend.mom_growth - (-0.1679)) < 0.002 (-16.8%)
       - anomalies contains period '2026-07'
    2. All 5 labeled anomalies in anomalies.yaml detected (>= 90% recall).
    3. 5 normal KPIs (du_no_dai_han, doanh_thu_thuan, tien_va_tuong_duong_tien,
       ty_le_no_tren_tong_nguon_von, ton_kho_sku for SYNTH_SKU_MFC18)
       have <= 1 false alarm per KPI per 12 months.
    """
    engine = get_ro_engine(profile="synth")

    # 1. du_no_ngan_han specific assertions
    trend_debt, warnings_debt, err_debt = analyze_kpi_trend(
        kpi_key="du_no_ngan_han",
        role="ceo",
        data_profile="synth",
        engine=engine,
    )
    assert err_debt is None, f"Query failed: {err_debt}"
    assert trend_debt is not None
    assert trend_debt.data_coverage == 12
    assert trend_debt.mom_growth is not None
    assert abs(trend_debt.mom_growth - (-0.1679)) < 0.002
    assert any("2026-07" in a.period for a in trend_debt.anomalies)

    # 2. Check all 5 labeled anomalies from anomalies.yaml
    with open(ANOMALIES_YAML, "r", encoding="utf-8") as f:
        anom_data = yaml.safe_load(f)
    labeled_list = anom_data.get("anomalies", [])

    detected_count = 0
    total_labeled = len(labeled_list)

    for item in labeled_list:
        kpi_key = item["kpi"]
        expected_period = item["period"][:7]  # normalize "2026-07-31" -> "2026-07"
        product_code = "SYNTH_SKU_MDF17" if kpi_key == "ton_kho_sku" else None

        trend_obj, warnings, err = analyze_kpi_trend(
            kpi_key=kpi_key,
            role="ceo",
            data_profile="synth",
            engine=engine,
            product_code=product_code,
        )
        assert err is None, f"Error analyzing {kpi_key}: {err}"
        assert trend_obj is not None

        # Check if expected period is in detected anomalies
        found = any(expected_period in anom.period for anom in trend_obj.anomalies)
        if found:
            detected_count += 1

    recall = detected_count / total_labeled
    assert recall >= 0.90, f"Anomaly recall {recall:.2%} < 90% ({detected_count}/{total_labeled})"

    # 3. Check 5 normal KPIs for false positives (M-10 <= 1 per KPI)
    normal_kpis = [
        ("du_no_dai_han", None),
        ("doanh_thu_thuan", None),
        ("tien_va_tuong_duong_tien", None),
        ("ty_le_no_tren_tong_nguon_von", None),
        ("ton_kho_sku", "SYNTH_SKU_MFC18"),
    ]

    for kpi_key, pcode in normal_kpis:
        trend_norm, _, err = analyze_kpi_trend(
            kpi_key=kpi_key,
            role="ceo",
            data_profile="synth",
            engine=engine,
            product_code=pcode,
        )
        assert err is None
        assert trend_norm is not None
        # False positives per KPI must be <= 1 (target 0)
        assert len(trend_norm.anomalies) <= 1, (
            f"Too many false alarms for normal KPI {kpi_key}: {[a.period for a in trend_norm.anomalies]}"
        )


def test_tc_t3_10_trend_honesty_when_real_revenue_has_single_month():
    """TC-T3-10:

    On real data warehouse, doanh_thu_thuan has only 1 month (2026-07).
    When data_coverage < 6:
    1. trend.data_coverage == 1
    2. trend.mom_growth is None
    3. trend.yoy_growth is None
    4. warnings contains exact warning: 'Chỉ có 1 tháng dữ liệu, chưa đủ để phân tích xu hướng'
    5. Zero fabricated growth rates.
    """
    engine = get_ro_engine(profile="real")

    trend_obj, warnings, err = analyze_kpi_trend(
        kpi_key="doanh_thu_thuan",
        role="ceo",
        data_profile="real",
        engine=engine,
    )

    assert err is None, f"Query failed: {err}"
    assert trend_obj is not None
    assert trend_obj.data_coverage == 1
    assert trend_obj.mom_growth is None
    assert trend_obj.yoy_growth is None
    assert any("Chỉ có 1 tháng dữ liệu, chưa đủ để phân tích xu hướng" in w for w in warnings)


def test_trend_role_permission_security_enforcement():
    """Role-based security: Role quan_ly_kho cannot access ai_v_no_vay views."""
    trend_obj, warnings, err = analyze_kpi_trend(
        kpi_key="du_no_ngan_han",
        role="quan_ly_kho",
        data_profile="synth",
    )
    assert trend_obj is None
    assert err is not None
    assert "quyền" in err.lower() or "không đủ" in err.lower() or "rejected" in err.lower()
