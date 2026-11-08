"""Unit tests for Task 2: T tầng Tri thức Ngữ nghĩa (T2), KPI Definitions, Business Rules,
Golden Query Matcher, RBAC Filtering, and Benchmark Leakage Prevention.

Specifications:
- Spec §5 T2, §6.9, §11.9, §11.10
- Plan Task 2 (T2)
- TC-T2-01: YAML Lint, 28 KPI Coverage (M-05 = 100%), Business Rules Disclaimers
- TC-T2-03: Benchmark 60-item Integrity and Zero Leakage (cosine < 0.92 & AST Skeleton Check)
- Review Focus #1: Golden Query RBAC filtering by role
- Review Focus #3: Dual leakage check (cosine similarity + AST skeleton identity)
"""

import pytest

from app.knowledge.lint_and_leakage import (
    check_benchmark_leakage,
    lint_knowledge_base,
    normalize_sql_ast_skeleton,
)
from app.knowledge.loader import (
    get_business_actions,
    get_kpi,
    load_benchmark,
    load_golden_queries,
    load_kpis,
    match_golden,
)
from app.knowledge.models import BenchmarkItem, GoldenQuery, KpiDefinition


def test_tc_t2_01_yaml_lint_and_m05_full_coverage():
    """TC-T2-01: Validate KPI definitions, full M-05 coverage (28/28), and business rules.

    - Exactly 28 KPIs in kpi_definitions.yaml covering all 5 BRD dashboards:
      D1 (8), D2 (6), D3 (6), D4 (5), D5 (3).
    - m05_coverage == 1.0 (all 28 KPIs have a valid golden query reference).
    - All threshold levels defined on KPIs have matching actions in business_rules.yaml.
    - All business rules contain the mandatory legal disclaimer.
    """
    ok, messages, m05_coverage = lint_knowledge_base()
    assert ok, f"lint_knowledge_base failed with messages: {messages}"
    assert m05_coverage == 1.0, f"Expected M-05 coverage 1.0 (100%), got {m05_coverage}"

    kpis = load_kpis()
    assert len(kpis) == 28, f"Expected exactly 28 KPIs, got {len(kpis)}"

    # Check dashboard counts
    dashboards = {}
    for kpi in kpis.values():
        dashboards[kpi.dashboard] = dashboards.get(kpi.dashboard, 0) + 1

    assert dashboards.get("D1", 0) == 8, f"Expected 8 KPIs in D1, got {dashboards.get('D1')}"
    assert dashboards.get("D2", 0) == 6, f"Expected 6 KPIs in D2, got {dashboards.get('D2')}"
    assert dashboards.get("D3", 0) == 6, f"Expected 6 KPIs in D3, got {dashboards.get('D3')}"
    assert dashboards.get("D4", 0) == 5, f"Expected 5 KPIs in D4, got {dashboards.get('D4')}"
    assert dashboards.get("D5", 0) == 3, f"Expected 3 KPIs in D5, got {dashboards.get('D5')}"

    # Verify business rules actions and mandatory disclaimer
    mandatory_disclaimer = "Gợi ý tham khảo từ quy tắc nghiệp vụ, cần người có thẩm quyền quyết định"
    for key, kpi in kpis.items():
        if kpi.nguong:
            for level in kpi.nguong.keys():
                rule = get_business_actions(key, level)
                assert rule is not None, f"Missing business rule for {key} at level {level}"
                assert len(rule["actions"]) > 0, f"Empty actions for {key} at level {level}"
                assert rule["authority_role"], f"Missing authority_role for {key} at level {level}"
                assert mandatory_disclaimer in rule["disclaimer"], (
                    f"Disclaimer missing mandatory clause for {key} at level {level}: {rule['disclaimer']}"
                )


def test_credit_limit_kpi_uses_uat_winning_formula():
    """Verify get_kpi('ty_le_su_dung_han_muc') uses principal_balance and granted_limit on ai_v_no_vay.

    Must NOT use du_no_ngan_han (per UAT winning formula from UAT_01).
    """
    kpi = get_kpi("ty_le_su_dung_han_muc")
    assert kpi.key == "ty_le_su_dung_han_muc"
    assert "ai_v_no_vay" in kpi.nguon_view
    formula = kpi.cong_thuc.lower()
    assert "principal_balance" in formula
    assert "granted_limit" in formula
    assert "du_no_ngan_han" not in formula


def test_match_golden_vietnamese_accented_and_unaccented():
    """Verify TF-IDF matching works for both unaccented and accented Vietnamese questions."""
    q_unaccented = "du no ngan han hien tai la bao nhieu"
    q_accented = "Dư nợ ngắn hạn hiện tại là bao nhiêu?"

    matches_unaccented = match_golden(q_unaccented, role="ceo", k=3)
    assert len(matches_unaccented) > 0, "No matches for unaccented query"
    top_unaccented = matches_unaccented[0]
    assert top_unaccented.query.kpi_key == "du_no_ngan_han"
    assert top_unaccented.similarity > 0.4

    matches_accented = match_golden(q_accented, role="ceo", k=3)
    assert len(matches_accented) > 0, "No matches for accented query"
    top_accented = matches_accented[0]
    assert top_accented.query.kpi_key == "du_no_ngan_han"
    assert top_accented.similarity > 0.4


def test_match_golden_filters_by_role_rbac():
    """Review Focus #1: Golden Query Matcher strictly filters by user role allowed views.

    - quan_ly_kho only has access to ai_v_ton_kho -> no match may use ai_v_no_vay.
    - quan_tri_he_thong has 0 views -> returns [] regardless of similarity.
    """
    matches_kho = match_golden("Dư nợ ngắn hạn hiện tại là bao nhiêu?", role="quan_ly_kho", k=3)
    for m in matches_kho:
        assert "ai_v_no_vay" not in m.query.views_used
        assert set(m.query.views_used).issubset({"ai_v_ton_kho"})

    matches_admin = match_golden("Dư nợ ngắn hạn hiện tại là bao nhiêu?", role="quan_tri_he_thong", k=3)
    assert matches_admin == [], f"Expected empty list for quan_tri_he_thong, got {matches_admin}"


def test_tc_t2_03_benchmark_no_leakage():
    """TC-T2-03: Validate benchmark 60 items integrity and ensure 0 leakage against Golden Queries.

    - Exactly 60 items: 40 dev and 20 test.
    - Every item has reviewed_by and reviewed_at populated.
    - check_benchmark_leakage(0.92) returns ok is True.
    """
    items = load_benchmark()
    assert len(items) == 60, f"Expected 60 benchmark items, got {len(items)}"

    dev_items = [item for item in items if item.split == "dev"]
    test_items = [item for item in items if item.split == "test"]
    assert len(dev_items) == 40, f"Expected 40 dev items, got {len(dev_items)}"
    assert len(test_items) == 20, f"Expected 20 test items, got {len(test_items)}"

    for item in items:
        assert item.reviewed_by and item.reviewed_by.strip(), f"Item {item.id} missing reviewed_by"
        assert item.reviewed_at and item.reviewed_at.strip(), f"Item {item.id} missing reviewed_at"

    ok, leakage_messages = check_benchmark_leakage(cosine_threshold=0.92)
    assert ok, f"Benchmark leakage detected: {leakage_messages}"


def test_leakage_detector_catches_identical_ast_with_rewritten_question():
    """Review Focus #3: check_benchmark_leakage detects AST skeleton leak even with rewritten question.

    If a test query has completely rewritten wording (cosine < 0.4) but its SQL is structurally
    identical to an existing Golden Query (modulo literals, aliases, whitespace),
    the detector must flag AST_SKELETON_LEAK and return ok is False.
    """
    # Create a synthetic test item whose question is completely different but AST skeleton
    # matches GQ_01 (du_no_ngan_han) with rewritten aliases and dates
    mock_test_item = BenchmarkItem(
        id="BENCH_SYNTH_LEAK_01",
        loai="sql",
        do_kho="de",
        split="test",
        profile="real",
        role="ceo",
        cau_hoi="Xin cho biet khoan no vay bank ngan han thang 6 ra sao",
        reference_sql=(
            "SELECT SUM(credit_balance) AS total_short_term "
            "FROM ai_views.ai_v_no_vay "
            "WHERE record_type = 'ledger_balance' "
            "  AND (account_no LIKE '34111%' OR account_no LIKE '34113%' OR account_no LIKE '34114%') "
            "  AND rn = 1;"
        ),
        expected_status="ok",
        reviewed_by="auditor",
        reviewed_at="2026-11-08",
    )

    ok, messages = check_benchmark_leakage(
        cosine_threshold=0.92,
        custom_test_items=[mock_test_item],
    )
    assert not ok, "Expected check_benchmark_leakage to fail for identical AST skeleton"
    assert any("AST_SKELETON_LEAK" in msg for msg in messages), f"Expected AST_SKELETON_LEAK in messages: {messages}"


def test_normalize_sql_ast_skeleton_table_alias_and_qualifiers():
    """Verify AST skeleton normalization strips table aliases and column qualifiers.

    Queries differing only by table alias or table qualifier
    (e.g. `FROM ai_views.ai_v_ton_kho t WHERE t.x = 1` vs `FROM ai_views.ai_v_ton_kho WHERE x = 1`)
    must produce identical normalized skeletons.
    """
    q1 = "FROM ai_views.ai_v_ton_kho t WHERE t.x = 1"
    q2 = "FROM ai_views.ai_v_ton_kho WHERE x = 1"
    assert normalize_sql_ast_skeleton(q1) == normalize_sql_ast_skeleton(q2)

    q3 = "SELECT t.ton_cuoi_ky AS ton FROM ai_views.ai_v_ton_kho t WHERE t.ma_kho = 'KHO1'"
    q4 = "SELECT ton_cuoi_ky FROM ai_views.ai_v_ton_kho WHERE ma_kho = 'KHO2'"
    assert normalize_sql_ast_skeleton(q3) == normalize_sql_ast_skeleton(q4)

