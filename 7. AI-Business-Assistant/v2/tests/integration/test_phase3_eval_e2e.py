"""Integration tests for Phase 3 Gate Verification (EV-06, EV-09, EV-10).

Specifications:
- TC-T8-02: Locked test split protection for RAG evaluation
- EV-06: M-03 (Hit@5) & M-04 (MRR) beat v1 baseline by >= 15 percentage points
- EV-09: M-09 (Anomaly recall >= 90%) & M-10 (False positive <= 1/KPI/12m)
- Live end-to-end analytical graph execution on real PostgreSQL & ChromaDB
"""

from pathlib import Path
import pytest

from app.orchestration.graph import build_analytical_graph
from app.orchestration.state import ChatState
from eval.run_eval import run_rag_evaluation, run_trend_evaluation


def test_rag_eval_locked_test_split_requires_final_flag():
    """TC-T8-02: Running RAG evaluation on test split without --final raises PermissionError."""
    with pytest.raises(PermissionError, match="TC-T8-02"):
        run_rag_evaluation(split="test", final=False)


def test_rag_eval_dev_beats_v1_by_15pp_and_generates_ev06(tmp_path):
    """EV-06: v2 Hybrid RAG beats v1 baseline on dev split by >= 15 pp on Hit@5 or MRR."""
    res = run_rag_evaluation(split="dev", final=False, output_dir=tmp_path)

    assert "report_path" in res
    report_file = Path(res["report_path"])
    assert report_file.exists()
    assert report_file.stat().st_size > 0

    v1_hit = res["v1_hit_at_5"]
    v2_hit = res["v2_hit_at_5"]
    v1_mrr = res["v1_mrr"]
    v2_mrr = res["v2_mrr"]

    # Either Hit@5 beats v1 by >= 15 pp or (v2_hit == 1.0 and MRR beats by >= 15 pp)
    hit_diff = v2_hit - v1_hit
    mrr_diff = v2_mrr - v1_mrr

    assert (hit_diff >= 0.15) or (v2_hit == 1.0 and mrr_diff >= 0.15), (
        f"v2 did not beat v1 by >= 15 pp: v1_hit={v1_hit:.2%}, v2_hit={v2_hit:.2%} (diff={hit_diff:+.2%}); "
        f"v1_mrr={v1_mrr:.2%}, v2_mrr={v2_mrr:.2%} (diff={mrr_diff:+.2%})"
    )


def test_trend_eval_meets_m09_and_m10_and_generates_ev09(tmp_path):
    """EV-09: TrendAnalyst detects synthetic anomalies with >= 90% recall and <= 1 FP/KPI."""
    res = run_trend_evaluation(output_dir=tmp_path)

    assert "report_path" in res
    report_file = Path(res["report_path"])
    assert report_file.exists()
    assert report_file.stat().st_size > 0

    assert res["m09_anomaly_recall"] >= 0.90, (
        f"Anomaly recall {res['m09_anomaly_recall']:.2%} < 90%"
    )
    assert res["m10_max_fp_per_kpi"] <= 1, (
        f"Max false positives per KPI {res['m10_max_fp_per_kpi']} > 1"
    )
    assert res["tc_t3_10_passed"] is True, "TC-T3-10 honest coverage check failed"


def test_live_analytical_graph_e2e_preview():
    """Live execution test of build_analytical_graph on PostgreSQL and ChromaDB.

    Evaluates 3 representative queries:
    1. sql_only: Dư nợ ngắn hạn (G-01) -> answer has figures and sql
    2. sql_only: Tỷ lệ sử dụng hạn mức (G-13) -> triggers Advice with severity level
    3. rag_only: Vòng quay các khoản phải thu -> answers with citations and sql is None
    """
    graph = build_analytical_graph()

    # Query 1: sql_only (G-01)
    state1: ChatState = {
        "request_id": "live-e2e-01",
        "user": {"id": "u-ceo", "role": "ceo"},
        "session_id": "sess-live-01",
        "query": "Dư nợ ngắn hạn hiện tại là bao nhiêu?",
        "data_profile": "real",
        "warnings": [],
        "errors": [],
        "trace": [],
    }
    out1 = graph.invoke(state1)
    ans1 = out1.get("answer", {})
    assert len(ans1.get("figures", [])) >= 1
    assert ans1.get("sql") is not None
    assert ans1.get("confidence", 0.0) >= 0.5

    # Query 2: sql_only with advice (G-13)
    state2: ChatState = {
        "request_id": "live-e2e-02",
        "user": {"id": "u-ceo", "role": "ceo"},
        "session_id": "sess-live-02",
        "query": "Tỷ lệ sử dụng hạn mức hiện tại là bao nhiêu?",
        "data_profile": "real",
        "warnings": [],
        "errors": [],
        "trace": [],
    }
    out2 = graph.invoke(state2)
    ans2 = out2.get("answer", {})
    assert len(ans2.get("figures", [])) >= 1
    assert len(ans2.get("advice", [])) >= 1
    assert ans2["advice"][0].get("level") in ("canh_bao", "nghiem_trong")

    # Query 3: rag_only
    state3: ChatState = {
        "request_id": "live-e2e-03",
        "user": {"id": "u-ceo", "role": "ceo"},
        "session_id": "sess-live-03",
        "query": "Công thức tính hệ số LTV trên Dashboard Tài chính là gì?",
        "intent": "rag_only",
        "data_profile": "real",
        "warnings": [],
        "errors": [],
        "trace": [],
    }
    out3 = graph.invoke(state3)
    ans3 = out3.get("answer", {})
    assert len(ans3.get("sources", [])) >= 1
    assert ans3.get("sql") is None
