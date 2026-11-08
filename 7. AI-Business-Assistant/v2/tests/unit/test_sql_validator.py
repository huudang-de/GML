"""Unit tests for sqlglot AST Validator and Role-Based Allowlist.

Adheres to:
- Spec §5 T3 (Safe AST SQL Verification)
- Spec §11.9 (Role-to-View Authorization Matrix)
- TC-T3-01: Blocks DML/DDL, multi-statement, forbidden functions, nested CTE DML
- TC-T3-02: Enforces role-based view allowlist and rejects raw silver.* / system schemas
- TC-T3-03: Enforces and caps LIMIT (default max 1000)
"""

import pytest
from app.core.errors import SqlRejected
from app.sql.validator import FORBIDDEN_FUNCS, validate, validate_for_role

CEO_VIEWS = {
    "ai_v_no_vay",
    "ai_v_dong_tien",
    "ai_v_bctc",
    "ai_v_ton_kho",
    "ai_v_cong_no",
    "ai_v_tien_gui",
    "ai_v_ke_hoach",
}


# ==============================================================================
# TC-T3-01: Destructive Statements, Multi-statement, and Forbidden Functions
# ==============================================================================


@pytest.mark.parametrize(
    "bad_sql",
    [
        "DELETE FROM ai_v_no_vay",
        "UPDATE ai_v_no_vay SET principal_balance = 0",
        "DROP TABLE ai_v_no_vay",
        "INSERT INTO ai_v_no_vay VALUES (1)",
        "CREATE TABLE exploit (id INT)",
        "ALTER TABLE ai_v_no_vay DROP COLUMN bank_code",
        "SELECT * FROM ai_v_no_vay; DROP TABLE ai_v_no_vay;",
        "SELECT 1; SELECT 2;",
        "SELECT pg_sleep(20) FROM ai_v_no_vay",
        "SELECT pg_read_file('/etc/passwd') FROM ai_v_no_vay",
        "SELECT dblink('host=evil', 'SELECT 1') FROM ai_v_no_vay",
        "SELECT lo_import('/etc/shadow') FROM ai_v_no_vay",
        "WITH d AS (DELETE FROM ai_v_no_vay RETURNING *) SELECT * FROM d",
        "WITH u AS (UPDATE ai_v_no_vay SET principal_balance = 0 RETURNING *) SELECT * FROM u",
        "SELECT * FROM ai_v_no_vay FOR UPDATE",
        "SELECT * INTO new_table FROM ai_v_no_vay",
    ],
)
def test_tc_t3_01_validator_blocks_destructive_multi_and_forbidden_funcs(bad_sql):
    """TC-T3-01: DELETE, UPDATE, DROP, INSERT, multi-statement, pg_sleep -> SqlRejected."""
    with pytest.raises(SqlRejected):
        validate(bad_sql, allowed_tables=CEO_VIEWS)


def test_tc_t3_01_validator_blocks_empty_and_syntax_error():
    """Empty SQL or unparseable syntax must raise SqlRejected."""
    with pytest.raises(SqlRejected, match="rỗng|không hợp lệ"):
        validate("", allowed_tables=CEO_VIEWS)

    with pytest.raises(SqlRejected, match="rỗng|không hợp lệ"):
        validate("   \n\t  ", allowed_tables=CEO_VIEWS)

    with pytest.raises(SqlRejected, match="Lỗi cú pháp"):
        validate("SELECT FROM WHERE", allowed_tables=CEO_VIEWS)


def test_tc_t3_01_forbidden_funcs_constant_matches_spec():
    """Verify all forbidden functions are present in FORBIDDEN_FUNCS."""
    expected = {
        "pg_sleep", "pg_read_file", "pg_read_binary_file",
        "pg_ls_dir", "pg_stat_file", "lo_import", "lo_export",
        "dblink", "dblink_exec", "query_to_xml",
    }
    assert expected.issubset(FORBIDDEN_FUNCS)


# ==============================================================================
# TC-T3-02: Role-Based Allowlist & Schema Boundary Protection
# ==============================================================================


def test_tc_t3_02_validator_blocks_disallowed_table_for_role():
    """TC-T3-02: Role quan_ly_kho querying ai_v_no_vay -> SqlRejected."""
    with pytest.raises(SqlRejected, match="ai_v_no_vay"):
        validate_for_role("SELECT * FROM ai_v_no_vay", role="quan_ly_kho")

    # Allowed view for quan_ly_kho succeeds:
    out = validate_for_role("SELECT * FROM ai_v_ton_kho", role="quan_ly_kho")
    assert "ai_v_ton_kho" in out.lower()


def test_tc_t3_02_validator_blocks_unauthorized_roles():
    """Roles with zero views (quan_tri_he_thong, unknown) are rejected immediately."""
    with pytest.raises(SqlRejected, match="không có quyền"):
        validate_for_role("SELECT * FROM ai_v_ton_kho", role="quan_tri_he_thong")

    with pytest.raises(SqlRejected, match="không có quyền"):
        validate_for_role("SELECT * FROM ai_v_ton_kho", role="anonymous_guest")


def test_tc_t3_02_validator_blocks_raw_silver_schema_even_for_ceo():
    """Review Focus #1: Direct access to silver.*, pg_catalog.*, or foreign schemas is rejected."""
    with pytest.raises(SqlRejected, match="Schema không được phép: silver"):
        validate("SELECT * FROM silver.fact_cashflow", allowed_tables=CEO_VIEWS)

    with pytest.raises(SqlRejected, match="Schema không được phép: silver"):
        validate("SELECT * FROM silver.ai_v_no_vay", allowed_tables=CEO_VIEWS)

    with pytest.raises(SqlRejected, match="Schema không được phép: pg_catalog"):
        validate("SELECT * FROM pg_catalog.pg_tables", allowed_tables=CEO_VIEWS)

    with pytest.raises(SqlRejected, match="Schema không được phép: information_schema"):
        validate("SELECT * FROM information_schema.tables", allowed_tables=CEO_VIEWS)


def test_tc_t3_02_validator_blocks_unregistered_bare_tables():
    """Tables not in the allowlist even without schema prefix must be rejected."""
    with pytest.raises(SqlRejected, match="Bảng không được phép: fact_cashflow"):
        validate("SELECT * FROM fact_cashflow", allowed_tables=CEO_VIEWS)

    with pytest.raises(SqlRejected, match="Bảng không được phép: users"):
        validate("SELECT * FROM users", allowed_tables=CEO_VIEWS)


# ==============================================================================
# TC-T3-03: LIMIT Enforcement and Capping
# ==============================================================================


def test_tc_t3_03_validator_enforces_and_caps_limit():
    """TC-T3-03 & Review Focus #2: Missing LIMIT gets added; excessive LIMIT gets capped."""
    sql_no_limit = "SELECT bank_code, granted_limit FROM ai_views.ai_v_no_vay"
    out = validate(sql_no_limit, allowed_tables=CEO_VIEWS, max_rows=1000)
    assert "LIMIT 1000" in out.upper()

    sql_huge_limit = "SELECT bank_code FROM ai_v_no_vay LIMIT 50000"
    out_capped = validate(sql_huge_limit, allowed_tables=CEO_VIEWS, max_rows=1000)
    assert "LIMIT 1000" in out_capped.upper()
    assert "50000" not in out_capped


def test_tc_t3_03_validator_preserves_smaller_limit():
    """Explicit LIMIT <= max_rows must be preserved."""
    sql = "SELECT bank_code FROM ai_views.ai_v_no_vay LIMIT 50"
    out = validate(sql, allowed_tables=CEO_VIEWS, max_rows=1000)
    assert "LIMIT 50" in out.upper()


def test_tc_t3_03_validator_union_limit_handling():
    """UNION queries must also have LIMIT enforced or capped at outer query level."""
    sql_union = "SELECT bank_code FROM ai_views.ai_v_no_vay UNION ALL SELECT bank_code FROM ai_views.ai_v_no_vay"
    out = validate(sql_union, allowed_tables=CEO_VIEWS, max_rows=1000)
    assert "LIMIT 1000" in out.upper()

    sql_union_excessive = (
        "SELECT bank_code FROM ai_views.ai_v_no_vay UNION ALL "
        "SELECT bank_code FROM ai_views.ai_v_no_vay LIMIT 99999"
    )
    out_capped = validate(sql_union_excessive, allowed_tables=CEO_VIEWS, max_rows=1000)
    assert "LIMIT 1000" in out_capped.upper()
    assert "99999" not in out_capped


# ==============================================================================
# CTEs, Subqueries, and Complex Queries
# ==============================================================================


def test_validator_allows_cte_and_subqueries_on_allowed_views():
    """Complex CTEs and subqueries on allowed views are accepted."""
    sql = """
    WITH latest AS (
        SELECT bank_code, principal_balance
        FROM ai_views.ai_v_no_vay
    )
    SELECT bank_code, SUM(principal_balance) AS total
    FROM latest
    GROUP BY bank_code
    LIMIT 10
    """
    out = validate(sql, allowed_tables=CEO_VIEWS)
    assert "LIMIT 10" in out.upper()
    assert "latest" in out.lower()


def test_validator_detects_disallowed_table_in_cte():
    """A CTE referencing a disallowed table or schema must be rejected."""
    sql = """
    WITH sneaky AS (
        SELECT * FROM silver.dim_customers
    )
    SELECT * FROM sneaky
    """
    with pytest.raises(SqlRejected, match="silver"):
        validate(sql, allowed_tables=CEO_VIEWS)


def test_validator_detects_disallowed_table_in_subquery():
    """Subquery referencing an unauthorized view must be rejected."""
    sql = """
    SELECT item_code, quantity_on_hand
    FROM ai_views.ai_v_ton_kho
    WHERE item_code IN (SELECT bank_code FROM ai_views.ai_v_no_vay)
    """
    # quan_ly_kho only has ai_v_ton_kho, not ai_v_no_vay
    with pytest.raises(SqlRejected, match="ai_v_no_vay"):
        validate_for_role(sql, role="quan_ly_kho")


def test_validator_case_insensitivity_and_schema_prefix():
    """Queries with varying case and ai_views schema prefix should succeed."""
    sql = "SELECT BANK_CODE FROM AI_VIEWS.AI_V_NO_VAY WHERE PRINCIPAL_BALANCE > 0"
    out = validate_for_role(sql, role="ceo")
    assert "ai_v_no_vay" in out.lower()
    assert "LIMIT 1000" in out.upper()
