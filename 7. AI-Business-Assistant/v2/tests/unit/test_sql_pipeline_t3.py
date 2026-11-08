"""Unit tests for Task 3: Read-only SQL executor, Self-repair loop, and Confidence Scorer.

Specifications:
- Spec §5 T3 (Read-only SQL Engine & Confidence Scorer)
- TC-T3-04: Execution classification (ok, no_data, execution_error)
- TC-T3-05: Sanitization of DB execution errors
- TC-T3-06: Self-repair loop (<= 3 attempts, cap at 3)
- TC-T3-07: Confidence scoring rules (gate, golden similarity, consistency, plausibility)
- Review Focus #2: Aggregate query with all NULL values treated as no_data
- Review Focus #5: Sanitization of DB errors before repair_fn and log
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, call
import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from app.core.errors import SqlRejected
from app.knowledge.models import KpiDefinition
from app.sql import (
    ConfidenceBreakdown,
    RepairAttempt,
    SqlDraft,
    SqlExecutionResult,
    SqlStatus,
    execute_validated_sql,
    run_validate_execute_with_repair,
    score_sql_confidence,
)


# ==============================================================================
# TC-T3-04 & Review Focus #2: SQL Executor Tests
# ==============================================================================

def test_tc_t3_04_empty_rows_returns_no_data():
    """Mock DB returns 0 rows -> status == 'no_data', row_count == 0, error is None."""
    mock_engine = MagicMock(spec=Engine)
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    mock_cursor = MagicMock()
    mock_cursor.returns_rows = True
    mock_cursor.keys.return_value = ["bank_code", "balance"]
    mock_cursor.fetchmany.return_value = []
    mock_conn.execute.return_value = mock_cursor

    sql = "SELECT bank_code, balance FROM ai_views.ai_v_no_vay WHERE 1=0 LIMIT 1000"
    res = execute_validated_sql(sql, engine=mock_engine)

    assert res.status == "no_data"
    assert res.row_count == 0
    assert res.rows == []
    assert res.error is None
    assert res.sql == sql
    assert res.columns == ["bank_code", "balance"]
    assert res.latency_ms >= 0.0


def test_executor_all_null_aggregate_row_returns_no_data():
    """Review Focus #2: Mock DB returns 1 row with all None -> status == 'no_data', rows == [], row_count == 0.

    In PostgreSQL, SELECT SUM(...) WHERE 1=0 returns [(None,)], row_count=1.
    Must be normalized to status='no_data', rows=[], row_count=0.
    """
    mock_engine = MagicMock(spec=Engine)
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    mock_cursor = MagicMock()
    mock_cursor.returns_rows = True
    mock_cursor.keys.return_value = ["sum"]
    mock_cursor.fetchmany.return_value = [{"sum": None}]
    mock_conn.execute.return_value = mock_cursor

    sql = "SELECT SUM(credit_balance) FROM ai_views.ai_v_no_vay WHERE 1=0 LIMIT 1000"
    res = execute_validated_sql(sql, engine=mock_engine)

    assert res.status == "no_data"
    assert res.rows == []
    assert res.row_count == 0
    assert res.error is None
    assert res.columns == ["sum"]


def test_executor_normal_rows_serialization():
    """Normal query returns Decimal, date, float, str, uuid -> converted cleanly, status == 'ok'."""
    import uuid
    test_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")

    mock_engine = MagicMock(spec=Engine)
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    mock_cursor = MagicMock()
    mock_cursor.returns_rows = True
    mock_cursor.keys.return_value = ["row_id", "bank_name", "credit_limit", "effective_date"]
    mock_cursor.fetchmany.return_value = [
        {
            "row_id": test_uuid,
            "bank_name": "Vietcombank",
            "credit_limit": Decimal("295000000000.00"),
            "effective_date": date(2026, 7, 31),
        }
    ]
    mock_conn.execute.return_value = mock_cursor

    sql = "SELECT row_id, bank_name, credit_limit, effective_date FROM ai_views.ai_v_no_vay LIMIT 10"
    res = execute_validated_sql(sql, engine=mock_engine)

    assert res.status == "ok"
    assert res.row_count == 1
    assert len(res.rows) == 1
    assert res.rows[0]["row_id"] == "12345678-1234-5678-1234-567812345678"
    assert res.rows[0]["bank_name"] == "Vietcombank"
    assert isinstance(res.rows[0]["credit_limit"], float)
    assert res.rows[0]["credit_limit"] == 295000000000.0
    assert res.rows[0]["effective_date"] == "2026-07-31"
    assert res.error is None


# ==============================================================================
# TC-T3-05: DB Error Sanitization Tests
# ==============================================================================

def test_tc_t3_05_db_error_returns_sanitized_execution_error():
    """Mock DB raises OperationalError with credentials and schema -> status == 'execution_error', sanitized."""
    mock_engine = MagicMock(spec=Engine)
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    raw_err_msg = (
        "FATAL: password authentication failed for postgresql://dev:Secret123@localhost/gml "
        "on relation silver.fact_cashflow"
    )
    mock_conn.execute.side_effect = OperationalError(
        statement="SELECT * FROM silver.fact_cashflow",
        params={},
        orig=Exception(raw_err_msg),
    )

    sql = "SELECT * FROM ai_views.ai_v_dong_tien LIMIT 1000"
    res = execute_validated_sql(sql, engine=mock_engine)

    assert res.status == "execution_error"
    assert res.rows == []
    assert res.row_count == 0
    assert res.error is not None
    assert "Secret123" not in res.error
    assert "silver." not in res.error
    assert "[REDACTED_SCHEMA]." in res.error
    assert "[REDACTED_CREDENTIALS]@" in res.error


# ==============================================================================
# TC-T3-06 & Review Focus #5: Self-Repair Loop Tests
# ==============================================================================

def test_tc_t3_06_self_repair_succeeds_on_third_attempt_and_caps_at_three():
    """Scenario A: Attempt 1 syntax/table error, attempt 2 DB column error, attempt 3 succeeds.

    Result: status == 'ok', len(attempts) == 3, attempt_no == [1, 2, 3].
    """
    allowed_views = {"ai_v_no_vay"}

    sql_v1 = "SELECT * FROM invalid_table"  # Will fail AST validation
    sql_v2 = "SELECT non_existent_col FROM ai_views.ai_v_no_vay LIMIT 10"  # AST pass, exec fail
    sql_v3 = "SELECT credit_limit FROM ai_views.ai_v_no_vay LIMIT 10"  # Success

    def mock_repair(broken_sql: str, sanitized_err: str) -> str:
        if "invalid_table" in broken_sql:
            return sql_v2
        return sql_v3

    repair_mock = MagicMock(side_effect=mock_repair)

    def mock_execute(sql: str) -> SqlExecutionResult:
        if "non_existent_col" in sql:
            return SqlExecutionResult(
                status="execution_error",
                sql=sql,
                columns=[],
                rows=[],
                row_count=0,
                error="column non_existent_col does not exist",
            )
        return SqlExecutionResult(
            status="ok",
            sql=sql,
            columns=["credit_limit"],
            rows=[{"credit_limit": 1000000.0}],
            row_count=1,
            error=None,
        )

    res, attempts = run_validate_execute_with_repair(
        initial_sql=sql_v1,
        allowed_views=allowed_views,
        execute_fn=mock_execute,
        repair_fn=repair_mock,
        max_attempts=3,
    )

    assert res.status == "ok"
    assert len(attempts) == 3
    assert [a.attempt_no for a in attempts] == [1, 2, 3]
    assert attempts[0].stage == "ast"
    assert attempts[0].status == "rejected"
    assert attempts[1].stage == "exec"
    assert attempts[1].status == "execution_error"
    assert attempts[2].stage == "ok"
    assert attempts[2].status == "ok"
    assert repair_mock.call_count == 2


def test_tc_t3_06_self_repair_caps_at_three_on_persistent_failure():
    """Scenario B: Persistent failure across all attempts -> stops at 3 attempts, repair_fn called exactly 2 times."""
    allowed_views = {"ai_v_no_vay"}
    broken_sql = "SELECT * FROM forbidden_view"

    repair_mock = MagicMock(return_value="SELECT * FROM still_forbidden")

    res, attempts = run_validate_execute_with_repair(
        initial_sql=broken_sql,
        allowed_views=allowed_views,
        execute_fn=MagicMock(),
        repair_fn=repair_mock,
        max_attempts=3,
    )

    assert res.status == "rejected"
    assert len(attempts) == 3
    assert repair_mock.call_count == 2  # After attempt 1 and attempt 2; attempt 3 terminates


def test_repair_sanitizes_db_error_before_llm_prompt_and_log():
    """Review Focus #5: execute_fn returns raw error with silver.* or filesystem path -> sanitized before repair_fn and in attempts."""
    allowed_views = {"ai_v_no_vay"}
    initial_sql = "SELECT * FROM ai_views.ai_v_no_vay LIMIT 10"

    raw_leak_error = (
        "relation silver.fact_loan not accessible in config file D:\\secret\\db.cfg line 42"
    )

    def leaking_execute(sql: str) -> SqlExecutionResult:
        return SqlExecutionResult(
            status="execution_error",
            sql=sql,
            columns=[],
            rows=[],
            row_count=0,
            error=raw_leak_error,
        )

    captured_repair_args = []

    def tracking_repair(sql: str, sanitized_err: str) -> str:
        captured_repair_args.append((sql, sanitized_err))
        return "SELECT credit_limit FROM ai_views.ai_v_no_vay LIMIT 10"

    res, attempts = run_validate_execute_with_repair(
        initial_sql=initial_sql,
        allowed_views=allowed_views,
        execute_fn=leaking_execute,
        repair_fn=tracking_repair,
        max_attempts=2,
    )

    # Check that repair_fn received sanitized error
    assert len(captured_repair_args) >= 1
    passed_err = captured_repair_args[0][1]
    assert "silver." not in passed_err
    assert "[REDACTED_SCHEMA]." in passed_err
    assert "D:\\secret\\db.cfg" not in passed_err
    assert "[REDACTED_PATH]" in passed_err

    # Check that attempts[0].sanitized_error is sanitized
    assert "silver." not in attempts[0].sanitized_error
    assert "[REDACTED_SCHEMA]." in attempts[0].sanitized_error
    assert "[REDACTED_PATH]" in attempts[0].sanitized_error


def test_repair_fn_exception_is_cleanly_caught():
    """Verify that an unexpected exception in repair_fn does not crash the loop.

    Instead, records a RepairAttempt with stage='repair_fn', status='execution_error',
    and gracefully returns last_result and the recorded attempts.
    """
    allowed_views = {"ai_v_no_vay"}
    broken_sql = "SELECT * FROM invalid_table"

    def crashing_repair(sql: str, err: str) -> str:
        raise RuntimeError("Ollama connection failed: connection refused to 127.0.0.1:11434")

    res, attempts = run_validate_execute_with_repair(
        initial_sql=broken_sql,
        allowed_views=allowed_views,
        execute_fn=MagicMock(),
        repair_fn=crashing_repair,
        max_attempts=3,
    )

    assert res.status == "rejected"
    assert len(attempts) == 2
    # Attempt 1: AST validation rejected
    assert attempts[0].stage == "ast"
    assert attempts[0].status == "rejected"
    # Attempt 2: repair_fn failure cleanly captured
    assert attempts[1].stage == "repair_fn"
    assert attempts[1].status == "execution_error"
    assert "Repair function failed" in attempts[1].sanitized_error



# ==============================================================================
# TC-T3-07: Confidence Scoring Rules Tests
# ==============================================================================

def test_tc_t3_07_confidence_scoring_rules_identical_candidates():
    """3 candidate SQLs with same results (different alias names/order) -> consistency == 1.0, plausibility == 1.0."""
    res1 = SqlExecutionResult(
        status="ok",
        sql="SELECT SUM(credit_balance) AS tong_du_no FROM ai_views.ai_v_no_vay",
        columns=["tong_du_no"],
        rows=[{"tong_du_no": 236065233815.00}],
        row_count=1,
    )
    res2 = SqlExecutionResult(
        status="ok",
        sql="SELECT SUM(credit_balance) AS sum_credit FROM ai_views.ai_v_no_vay",
        columns=["sum_credit"],
        rows=[{"sum_credit": 236065233815.00}],
        row_count=1,
    )
    res3 = SqlExecutionResult(
        status="ok",
        sql="SELECT SUM(credit_balance) AS val FROM ai_views.ai_v_no_vay",
        columns=["val"],
        rows=[{"val": 236065233815.00001}],  # Within 6 significant digits
        row_count=1,
    )

    kpi = KpiDefinition(
        key="du_no_ngan_han",
        ten="Dư nợ ngắn hạn",
        dashboard="D1",
        don_vi="VND",
        cong_thuc="SUM(credit_balance)",
        nguon_view=["ai_v_no_vay"],
        golden_ref="G-01",
        y_nghia="Tổng dư nợ",
        plausible_range=(0.0, 1e14),
    )

    breakdown = score_sql_confidence(
        primary_result=res1,
        golden_similarity=0.9,
        candidate_results=[res1, res2, res3],
        kpi_def=kpi,
    )

    assert breakdown.passed_mandatory_gate is True
    assert breakdown.golden_similarity == pytest.approx(0.9)
    assert breakdown.consistency == pytest.approx(1.0)
    assert breakdown.plausibility == pytest.approx(1.0)
    expected_total = 0.3 * 0.9 + 0.4 * 1.0 + 0.3 * 1.0  # 0.97
    assert breakdown.total == pytest.approx(expected_total)


def test_tc_t3_07_confidence_scoring_no_data_yields_zero_plausibility():
    """status == 'no_data' -> plausibility == 0.0, mandatory gate passes, total = 0.3*sim + 0.4*consist."""
    res_no_data = SqlExecutionResult(
        status="no_data",
        sql="SELECT * FROM ai_views.ai_v_no_vay WHERE 1=0",
        columns=["col"],
        rows=[],
        row_count=0,
    )

    breakdown = score_sql_confidence(
        primary_result=res_no_data,
        golden_similarity=0.8,
        candidate_results=[res_no_data],
    )

    assert breakdown.passed_mandatory_gate is True
    assert breakdown.plausibility == 0.0
    assert breakdown.consistency == 1.0
    assert breakdown.total == pytest.approx(0.3 * 0.8 + 0.4 * 1.0 + 0.3 * 0.0)


def test_tc_t3_07_confidence_scoring_mandatory_gate_blocks_errors():
    """status == 'rejected' or 'execution_error' -> mandatory gate fails, total == 0.0."""
    res_rejected = SqlExecutionResult(
        status="rejected",
        sql="DELETE FROM ai_views.ai_v_no_vay",
        columns=[],
        rows=[],
        row_count=0,
        error="DML not allowed",
    )

    breakdown_rejected = score_sql_confidence(
        primary_result=res_rejected,
        golden_similarity=0.95,
    )
    assert breakdown_rejected.passed_mandatory_gate is False
    assert breakdown_rejected.total == 0.0

    res_exec_err = SqlExecutionResult(
        status="execution_error",
        sql="SELECT non_existent FROM ai_views.ai_v_no_vay",
        columns=[],
        rows=[],
        row_count=0,
        error="Column not found",
    )
    breakdown_exec = score_sql_confidence(
        primary_result=res_exec_err,
        golden_similarity=0.99,
    )
    assert breakdown_exec.passed_mandatory_gate is False
    assert breakdown_exec.total == 0.0


def test_tc_t3_07_confidence_scoring_out_of_plausible_range():
    """Value outside kpi_def.plausible_range -> plausibility <= 0.2."""
    res = SqlExecutionResult(
        status="ok",
        sql="SELECT 250.0 AS ty_le_su_dung_han_muc",
        columns=["ty_le_su_dung_han_muc"],
        rows=[{"ty_le_su_dung_han_muc": 250.0}],
        row_count=1,
    )

    kpi = KpiDefinition(
        key="ty_le_su_dung_han_muc",
        ten="Tỷ lệ sử dụng hạn mức",
        dashboard="D1",
        don_vi="%",
        cong_thuc="SUM(principal_balance)/SUM(granted_limit)",
        nguon_view=["ai_v_no_vay"],
        golden_ref="G-13",
        y_nghia="Tỷ lệ",
        plausible_range=(0.0, 5.0),  # Max plausible ratio is 500% (5.0)
    )

    breakdown = score_sql_confidence(
        primary_result=res,
        golden_similarity=0.9,
        candidate_results=[res],
        kpi_def=kpi,
    )

    assert breakdown.passed_mandatory_gate is True
    assert breakdown.plausibility <= 0.2


def test_confidence_scoring_partial_candidate_consistency():
    """2 out of 3 candidates agree -> consistency == pytest.approx(2/3)."""
    res1 = SqlExecutionResult(
        status="ok",
        sql="SELECT 100",
        columns=["val"],
        rows=[{"val": 100}],
        row_count=1,
    )
    res2 = SqlExecutionResult(
        status="ok",
        sql="SELECT 100",
        columns=["val"],
        rows=[{"val": 100}],
        row_count=1,
    )
    res3 = SqlExecutionResult(
        status="ok",
        sql="SELECT 999",
        columns=["val"],
        rows=[{"val": 999}],
        row_count=1,
    )

    breakdown = score_sql_confidence(
        primary_result=res1,
        golden_similarity=0.5,
        candidate_results=[res1, res2, res3],
    )

    assert breakdown.consistency == pytest.approx(2 / 3)


# ==============================================================================
# Model schemas verification
# ==============================================================================

def test_sql_models_schemas():
    """Verify SqlDraft and RepairAttempt model structures and defaults."""
    draft = SqlDraft(sql="SELECT 1", explanation_short="Test query")
    assert draft.sql == "SELECT 1"
    assert draft.explanation_short == "Test query"
    assert draft.kpi_keys == []
    assert draft.out_of_scope_reason is None

    attempt = RepairAttempt(
        attempt_no=1,
        sql="SELECT 1",
        stage="ok",
        status="ok",
    )
    assert attempt.attempt_no == 1
    assert attempt.sanitized_error is None
