"""Unit tests for Task 3: TrendAnalyst and DecisionAdvisor.

Specifications:
- Spec §5 T3 (TrendAnalyst & DecisionAdvisor)
- Review Focus #3: MAD fallback when MAD == 0 and false-positive suppression on rebound month
- TC-T3-11: DecisionAdvisor strict allowlist filtering out unauthorized LLM actions
- TC-T3-12: Mandatory authority disclaimer enforcement on all advice
- CFO Playbooks (SOP-01..04) and GML 4-Quarter Seasonality Insights
"""

import pytest
from pydantic import ValidationError

from app.agents.models import Advice, TrendAnomaly, TrendPoint
from app.agents.llm_text import MockTextLLMClient
from app.knowledge.loader import (
    get_seasonality_insight,
    load_cfo_playbooks,
    match_cfo_playbooks,
)
from app.agents.trend_agent import (
    create_trend_node,
    detect_series_anomalies,
)
from app.agents.advisor import (
    create_advise_node,
    evaluate_kpi_threshold_level,
    filter_approved_actions,
    run_advisor,
)
from app.orchestration.state import ChatState


# ==============================================================================
# 1. Review Focus #3: MAD == 0 & Rebound False-Positive Suppression
# ==============================================================================


def test_mad_zero_flat_series_detects_spike_and_suppresses_rebound_false_positive():
    """Review Focus #3:

    When 11 out of 12 months have identical values (5B) and month 2026-03 spikes to 18.5B:
    1. MAD of deviations is 0, so fallback scale must be used.
    2. Anomaly is accurately detected at 2026-03 (spike).
    3. The rebound month 2026-04 (returning to median 5B) has MoM = -73%, but must NOT
       be falsely flagged as an anomaly.
    """
    series = [
        TrendPoint(period="2025-08", value=5_000_000_000.0),
        TrendPoint(period="2025-09", value=5_000_000_000.0),
        TrendPoint(period="2025-10", value=5_000_000_000.0),
        TrendPoint(period="2025-11", value=5_000_000_000.0),
        TrendPoint(period="2025-12", value=5_000_000_000.0),
        TrendPoint(period="2026-01", value=5_000_000_000.0),
        TrendPoint(period="2026-02", value=5_000_000_000.0),
        TrendPoint(period="2026-03", value=18_500_000_000.0),  # Spike
        TrendPoint(period="2026-04", value=5_000_000_000.0),   # Rebound to median
        TrendPoint(period="2026-05", value=5_000_000_000.0),
        TrendPoint(period="2026-06", value=5_000_000_000.0),
        TrendPoint(period="2026-07", value=5_000_000_000.0),
    ]

    anomalies = detect_series_anomalies(
        kpi_key="ton_kho_sku",
        series=series,
        mom_threshold=0.15,
        mad_k=3.0,
    )

    # Exactly 1 anomaly detected at 2026-03
    assert len(anomalies) == 1, f"Expected 1 anomaly, found: {[a.period for a in anomalies]}"
    spike = anomalies[0]
    assert spike.period == "2026-03"
    assert spike.value == 18_500_000_000.0
    assert spike.severity in ["nghiem_trong", "canh_bao"]

    # 2026-04 must NOT be marked as an anomaly despite large negative MoM
    assert all(a.period != "2026-04" for a in anomalies)


# ==============================================================================
# 2. TC-T3-11: DecisionAdvisor Filters Out Unapproved LLM Action
# ==============================================================================


def test_tc_t3_11_advisor_filters_out_unapproved_llm_action():
    """TC-T3-11:

    For ty_le_su_dung_han_muc = 0.9182 (level: nghiem_trong), an LLM client
    attempting to inject an unauthorized action ('Thanh lý gấp nhà xưởng và bán bớt tài sản')
    is sanitized:
    1. advice[0].actions contains ONLY approved actions from business_rules.yaml.
    2. 'bán bớt tài sản' is strictly excluded.
    3. 'UNAPPROVED_ACTION_BLOCKED' warning is emitted.
    """
    mock_llm_response = (
        "- Kích hoạt phương án khẩn cấp: ngừng toàn bộ các khoản giải ngân mới chưa cấp thiết.\n"
        "- Thanh lý gấp nhà xưởng và bán bớt tài sản.\n"
        "- Thu hồi khẩn cấp các khoản phải thu quá hạn để thanh toán ngay nợ vay ngắn hạn đến hạn."
    )
    mock_client = MockTextLLMClient(response_text=mock_llm_response)

    sql_state = {
        "source_query_id": "test-sql-1",
        "rows": [{"ty_le_su_dung_han_muc": 0.9182}],
    }

    advices, warnings = run_advisor(
        kpi_keys=["ty_le_su_dung_han_muc"],
        sql_state=sql_state,
        llm_client=mock_client,
    )

    assert len(advices) >= 1
    primary_advice = next(a for a in advices if a.kpi_key == "ty_le_su_dung_han_muc")

    assert primary_advice.level == "nghiem_trong"
    assert primary_advice.authority_role == "ceo"

    # Action list does not contain unauthorized action
    for act in primary_advice.actions:
        assert "bán bớt tài sản" not in act.lower()
        assert "nhà xưởng" not in act.lower()

    # Must contain legitimate approved actions
    assert any("ngừng toàn bộ các khoản giải ngân" in act for act in primary_advice.actions)

    # UNAPPROVED_ACTION_BLOCKED warning present
    assert "UNAPPROVED_ACTION_BLOCKED" in warnings


# ==============================================================================
# 3. TC-T3-12: Mandatory Authority Disclaimer Enforcement
# ==============================================================================


def test_tc_t3_12_advisor_enforces_mandatory_authority_disclaimer():
    """TC-T3-12:

    1. All advice items from run_advisor must contain the mandated disclaimer.
    2. Level canh_bao maps to ke_toan_truong; level nghiem_trong maps to ceo.
    3. Direct instantiation of Advice with invalid disclaimer raises ValidationError.
    """
    mandatory_text = "Gợi ý tham khảo từ quy tắc nghiệp vụ, cần người có thẩm quyền quyết định"

    # Check canh_bao (0.80) -> ke_toan_truong
    advices_cb, _ = run_advisor(
        kpi_keys=["ty_le_su_dung_han_muc"],
        sql_state={"rows": [{"ty_le_su_dung_han_muc": 0.80}]},
    )
    adv_cb = next(a for a in advices_cb if a.kpi_key == "ty_le_su_dung_han_muc")
    assert adv_cb.level == "canh_bao"
    assert adv_cb.authority_role == "ke_toan_truong"
    assert adv_cb.disclaimer == mandatory_text

    # Check nghiem_trong (0.9182) -> ceo
    advices_nt, _ = run_advisor(
        kpi_keys=["ty_le_su_dung_han_muc"],
        sql_state={"rows": [{"ty_le_su_dung_han_muc": 0.9182}]},
    )
    adv_nt = next(a for a in advices_nt if a.kpi_key == "ty_le_su_dung_han_muc")
    assert adv_nt.level == "nghiem_trong"
    assert adv_nt.authority_role == "ceo"
    assert adv_nt.disclaimer == mandatory_text

    # Instantiating Advice without the required phrase fails
    with pytest.raises(ValidationError):
        Advice(
            kpi_key="ty_le_su_dung_han_muc",
            level="nghiem_trong",
            actions=["Hành động bất kỳ"],
            authority_role="ceo",
            disclaimer="Tự quyết định ngay",
        )


# ==============================================================================
# 4. CFO Playbooks & Seasonality Rules
# ==============================================================================


def test_cfo_playbooks_sop_trigger_and_seasonality_rules():
    """Verify CFO SOP-01..04 trigger conditions and 4-quarter seasonality insights.

    1. When dong_tien_rong = -45_000_000_000.0, SOP-01 (Cash Crunch SOP) activates
       with 3 immediate actions (lãi suất < 6.5%, chiết khấu 1-1.5%, đàm phán 10-15 ngày & dừng Capex).
    2. Seasonality for month 2 (post-Tet) returns Q1 wood industry context.
    """
    # 1. Cash Crunch SOP trigger
    advices, _ = run_advisor(
        kpi_keys=["dong_tien_rong"],
        sql_state={"rows": [{"dong_tien_rong": -45_000_000_000.0}]},
    )
    assert len(advices) >= 1
    sop01 = next(
        (a for a in advices if "SOP-01" in a.kpi_key or "Cash Crunch" in a.kpi_key),
        None,
    )
    assert sop01 is not None

    all_actions_text = " ".join(sop01.actions)
    assert "6.5%" in all_actions_text
    assert "1.0 - 1.5%" in all_actions_text or "1-1.5%" in all_actions_text or "1.0" in all_actions_text
    assert "10-15 ngày" in all_actions_text or "Capex" in all_actions_text

    # 2. Seasonality insight for month 2 (Q1)
    q1_insight = get_seasonality_insight(2)
    assert "thấp điểm" in q1_insight.lower()
    assert "tết" in q1_insight.lower()
    assert "tiền" in q1_insight.lower()

    # Seasonality for other quarters
    q2_insight = get_seasonality_insight(5)
    assert "nguyên liệu" in q2_insight.lower() or "sản xuất" in q2_insight.lower() or "ván" in q2_insight.lower()

    q4_insight = get_seasonality_insight(11)
    assert "cao điểm" in q4_insight.lower() or "bàn giao" in q4_insight.lower()


# ==============================================================================
# 5. Node Isolation & Helper Unit Tests
# ==============================================================================


def test_trend_node_state_isolation():
    """create_trend_node() writes ONLY 'trend', 'warnings', 'trace' (and optionally 'errors')."""
    node_fn = create_trend_node()
    state: ChatState = {
        "request_id": "req-1",
        "user": {"role": "ceo"},
        "kpi_keys": ["du_no_ngan_han"],
        "data_profile": "synth",
    }
    updates = node_fn(state)
    assert isinstance(updates, dict)
    allowed_keys = {"trend", "warnings", "trace", "errors"}
    assert set(updates.keys()).issubset(allowed_keys)
    assert "trend" in updates
    assert "warnings" in updates
    assert "trace" in updates


def test_advise_node_state_isolation():
    """create_advise_node() writes ONLY 'advice', 'warnings', 'trace'."""
    node_fn = create_advise_node()
    state: ChatState = {
        "request_id": "req-2",
        "user": {"role": "ceo"},
        "kpi_keys": ["ty_le_su_dung_han_muc"],
        "sql": {"rows": [{"ty_le_su_dung_han_muc": 0.9182}]},
    }
    updates = node_fn(state)
    assert isinstance(updates, dict)
    allowed_keys = {"advice", "warnings", "trace", "errors"}
    assert set(updates.keys()).issubset(allowed_keys)
    assert "advice" in updates
    assert "warnings" in updates
    assert "trace" in updates


def test_evaluate_kpi_threshold_level():
    """evaluate_kpi_threshold_level checks nghiem_trong before canh_bao."""
    # ty_le_su_dung_han_muc: canh_bao >= 0.70, nghiem_trong >= 0.90
    assert evaluate_kpi_threshold_level("ty_le_su_dung_han_muc", 0.65) is None
    assert evaluate_kpi_threshold_level("ty_le_su_dung_han_muc", 0.75) == "canh_bao"
    assert evaluate_kpi_threshold_level("ty_le_su_dung_han_muc", 0.95) == "nghiem_trong"

    # vong_quay_hang_ton_kho: canh_bao < 2.0, nghiem_trong < 1.0
    assert evaluate_kpi_threshold_level("vong_quay_hang_ton_kho", 3.0) is None
    assert evaluate_kpi_threshold_level("vong_quay_hang_ton_kho", 1.5) == "canh_bao"
    assert evaluate_kpi_threshold_level("vong_quay_hang_ton_kho", 0.8) == "nghiem_trong"


def test_filter_approved_actions():
    approved = [
        "Tạm dừng giải ngân mới từ các ngân hàng có tỷ lệ sử dụng trên 80%.",
        "Rà soát tiến độ thu hồi công nợ để ưu tiên trả bớt nợ gốc ngắn hạn.",
    ]
    candidates = [
        "Tạm dừng giải ngân mới từ các ngân hàng có tỷ lệ sử dụng trên 80%",  # Missing period
        "Bán bớt toàn bộ nhà máy",  # Unapproved
    ]
    filtered, has_unapproved = filter_approved_actions(candidates, approved)
    assert has_unapproved is True
    assert len(filtered) == 1
    assert "Tạm dừng giải ngân" in filtered[0]
