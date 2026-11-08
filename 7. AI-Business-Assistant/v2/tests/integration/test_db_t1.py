"""Integration tests for T1 Data Layer, Security Roles, Views, and Evidence Generation.

Specifications:
- Spec §3.1, §5 T1
- Spec §6 (Sổ đáp án chuẩn UAT: G-01..G-13)
- Spec §8 Phase 1 Gate (M-01 = 100%, M-02 = 0)
- TC-T1-01: Read-only enforcement (blocks INSERT/UPDATE/DELETE/DROP/CREATE)
- TC-T1-02: Raw silver schema isolation (permission denied for silver.*)
- TC-T1-03: Statement timeout enforcement (SHOW statement_timeout == 15s and query cancellation)
- TC-T1-04: View results match golden UAT numbers within relative error <= 1e-4
"""

from pathlib import Path
import pytest
import sqlalchemy as sa

from db.apply_db import (
    GOLD_UAT_QUERIES,
    apply_all,
    generate_t1_evidence,
    get_admin_engine,
    get_ro_engine,
)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Ensure roles, views, and app schema are deployed before running tests."""
    apply_all()


def test_tc_t1_01_ro_role_cannot_write():
    """TC-T1-01: gml_ai_ro cannot INSERT/UPDATE/DELETE/DROP/CREATE."""
    ro_engine = get_ro_engine()
    test_stmts = [
        "CREATE TABLE ai_views.hack_test (id int)",
        "DROP VIEW ai_views.ai_v_no_vay",
        "DELETE FROM ai_views.ai_v_no_vay",
        "UPDATE ai_views.ai_v_no_vay SET principal_balance = 0",
        "INSERT INTO ai_views.ai_v_no_vay (record_type) VALUES ('hack')",
    ]
    for stmt in test_stmts:
        with pytest.raises(Exception) as exc_info:
            with ro_engine.connect() as conn:
                conn.execute(sa.text(stmt))
                conn.commit()
        err_text = str(exc_info.value).lower()
        assert (
            "permission denied" in err_text
            or "read-only" in err_text
            or "cannot" in err_text
        ), f"Expected permission error for stmt: {stmt}, got: {err_text}"


def test_tc_t1_02_ro_role_cannot_read_raw_silver_schema():
    """TC-T1-02: SELECT * FROM silver.fact_cashflow by gml_ai_ro -> permission denied."""
    ro_engine = get_ro_engine()
    raw_silver_queries = [
        "SELECT * FROM silver.fact_cashflow LIMIT 1",
        "SELECT * FROM silver.fact_creditlimitsummary LIMIT 1",
        "SELECT * FROM silver.dim_account LIMIT 1",
    ]
    for query in raw_silver_queries:
        with pytest.raises(Exception) as exc_info:
            with ro_engine.connect() as conn:
                conn.execute(sa.text(query))
        assert "permission denied" in str(exc_info.value).lower(), f"Expected permission denied for: {query}"


def test_tc_t1_03_ro_role_statement_timeout():
    """TC-T1-03: statement_timeout is configured <= 15s and cancels long queries."""
    ro_engine = get_ro_engine()
    with ro_engine.connect() as conn:
        timeout_val = conn.execute(sa.text("SHOW statement_timeout")).scalar()
        assert timeout_val == "15s"

        # Verify cancellation using short local timeout (1s) so test suite stays fast while proving enforcement
        conn.execute(sa.text("SET LOCAL statement_timeout = '1s'"))
        with pytest.raises(Exception) as exc_info:
            conn.execute(sa.text("SELECT pg_sleep(3)"))
        err_msg = str(exc_info.value).lower()
        assert "statement timeout" in err_msg or "canceled" in err_msg


def test_tc_t1_04_views_match_uat_gold_answers():
    """TC-T1-04: Run golden queries on ai_views for G-01..G-13 with relative error <= 1e-4."""
    ro_engine = get_ro_engine()
    with ro_engine.connect() as conn:
        for item in GOLD_UAT_QUERIES:
            raw_res = conn.execute(sa.text(item["sql"])).scalar()
            assert raw_res is not None, f"Query returned None for {item['id']} ({item['name']})"
            actual = float(raw_res)
            expected = float(item["expected"])
            rel_err = abs(actual - expected) / max(abs(expected), 1e-9)
            assert rel_err <= 1e-4, (
                f"{item['id']} ({item['name']}): actual={actual}, expected={expected}, "
                f"rel_err={rel_err:.6e} exceeds tolerance 1e-4"
            )


def test_generate_ev01_and_ev02_evidence_files():
    """Verify EV-01 and EV-02 artefacts are generated and non-empty."""
    ev01_path, ev02_path = generate_t1_evidence()
    assert Path(ev01_path).exists(), f"Missing EV-01 file: {ev01_path}"
    assert Path(ev01_path).stat().st_size > 100, f"EV-01 file is too small: {ev01_path}"

    assert Path(ev02_path).exists(), f"Missing EV-02 file: {ev02_path}"
    assert Path(ev02_path).stat().st_size > 100, f"EV-02 file is too small: {ev02_path}"
