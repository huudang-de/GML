"""Self-repair loop for SQL generation and execution.

Specifications:
- Spec §5 T3 (Self-repair loop <= 3 attempts)
- Plan Task 3: T3-SQL Core Repair Loop
- Review Focus #5: DB/AST error sanitization before repair_fn and attempt logging
"""

from typing import Callable, Set

from app.core.errors import SqlRejected, sanitize_db_error
from app.sql.models import RepairAttempt, SqlExecutionResult
from app.sql.validator import validate


def run_validate_execute_with_repair(
    initial_sql: str,
    allowed_views: Set[str],
    execute_fn: Callable[[str], SqlExecutionResult],
    repair_fn: Callable[[str, str], str] | None = None,
    max_attempts: int = 3,
    max_rows: int = 1000,
) -> tuple[SqlExecutionResult, list[RepairAttempt]]:
    """Execute SQL with an automated self-repair loop capped at max_attempts (default: 3).

    Pipeline per attempt:
    1. AST Validation:
       - Calls validate(current_sql, allowed_tables=allowed_views, max_rows=max_rows).
       - On SqlRejected / syntax error: records attempt with stage='ast', status='rejected'.
       - Sanitizes error with sanitize_db_error() before logging or passing to repair_fn (Review Focus #5).
       - If attempts remain and repair_fn is provided, invokes repair_fn(current_sql, sanitized_err).
    2. Execution:
       - Invokes execute_fn(validated_sql).
       - If status in ('execution_error', 'rejected'): records attempt with stage='exec'.
       - Sanitizes any raw database error before passing to repair_fn (Review Focus #5).
       - If attempts remain and repair_fn is provided, invokes repair_fn(validated_sql, sanitized_err).
       - If status in ('ok', 'no_data'): records attempt with stage='ok', terminates immediately.

    Args:
        initial_sql: Initial candidate SQL statement.
        allowed_views: Allowlist of views for the caller's role.
        execute_fn: Execution function (e.g., execute_validated_sql).
        repair_fn: Optional repair function taking (broken_sql, sanitized_error) -> repaired_sql.
        max_attempts: Maximum number of repair attempts (default: 3).
        max_rows: Maximum rows allowed for LIMIT enforcement.

    Returns:
        tuple[SqlExecutionResult, list[RepairAttempt]]: Final execution result and full attempt history.
    """
    attempts: list[RepairAttempt] = []
    current_sql = initial_sql
    last_result: SqlExecutionResult | None = None

    for attempt_no in range(1, max_attempts + 1):
        # 1. AST Validation stage
        try:
            validated_sql = validate(
                current_sql,
                allowed_tables=allowed_views,
                max_rows=max_rows,
            )
        except SqlRejected as err:
            sanitized_err = sanitize_db_error(err)
            attempts.append(
                RepairAttempt(
                    attempt_no=attempt_no,
                    sql=current_sql,
                    stage="ast",
                    status="rejected",
                    sanitized_error=sanitized_err,
                )
            )
            last_result = SqlExecutionResult(
                status="rejected",
                sql=current_sql,
                columns=[],
                rows=[],
                row_count=0,
                error=sanitized_err,
                latency_ms=0.0,
            )
            if attempt_no < max_attempts and repair_fn is not None:
                try:
                    current_sql = repair_fn(current_sql, sanitized_err)
                    continue
                except Exception as exc:
                    # LLM provider / network failure during repair attempt
                    # Record attempt and stop further repair, returning last_result
                    attempts.append(
                        RepairAttempt(
                            attempt_no=attempt_no,
                            stage="repair_fn",
                            status="execution_error",
                            sql=current_sql,
                            sanitized_error=f"Repair function failed: {sanitize_db_error(exc)}",
                        )
                    )
                    break
            else:
                break
        except Exception as err:
            sanitized_err = sanitize_db_error(err)
            attempts.append(
                RepairAttempt(
                    attempt_no=attempt_no,
                    sql=current_sql,
                    stage="ast",
                    status="rejected",
                    sanitized_error=sanitized_err,
                )
            )
            last_result = SqlExecutionResult(
                status="rejected",
                sql=current_sql,
                columns=[],
                rows=[],
                row_count=0,
                error=sanitized_err,
                latency_ms=0.0,
            )
            if attempt_no < max_attempts and repair_fn is not None:
                try:
                    current_sql = repair_fn(current_sql, sanitized_err)
                    continue
                except Exception as exc:
                    attempts.append(
                        RepairAttempt(
                            attempt_no=attempt_no,
                            stage="repair_fn",
                            status="execution_error",
                            sql=current_sql,
                            sanitized_error=f"Repair function failed: {sanitize_db_error(exc)}",
                        )
                    )
                    break
            else:
                break

        # 2. Execution stage
        exec_res = execute_fn(validated_sql)
        raw_error = exec_res.error or ""
        sanitized_exec_err = sanitize_db_error(raw_error) if raw_error else None

        if exec_res.status == "execution_error":
            attempts.append(
                RepairAttempt(
                    attempt_no=attempt_no,
                    sql=validated_sql,
                    stage="exec",
                    status="execution_error",
                    sanitized_error=sanitized_exec_err,
                )
            )
            last_result = exec_res.model_copy(update={"error": sanitized_exec_err})
            if attempt_no < max_attempts and repair_fn is not None:
                try:
                    current_sql = repair_fn(
                        validated_sql,
                        sanitized_exec_err or "Unknown execution error",
                    )
                    continue
                except Exception as exc:
                    attempts.append(
                        RepairAttempt(
                            attempt_no=attempt_no,
                            stage="repair_fn",
                            status="execution_error",
                            sql=validated_sql,
                            sanitized_error=f"Repair function failed: {sanitize_db_error(exc)}",
                        )
                    )
                    break
            else:
                break
        elif exec_res.status == "rejected":
            attempts.append(
                RepairAttempt(
                    attempt_no=attempt_no,
                    sql=validated_sql,
                    stage="exec",
                    status="rejected",
                    sanitized_error=sanitized_exec_err,
                )
            )
            last_result = exec_res.model_copy(update={"error": sanitized_exec_err})
            if attempt_no < max_attempts and repair_fn is not None:
                try:
                    current_sql = repair_fn(
                        validated_sql,
                        sanitized_exec_err or "Unknown rejection error",
                    )
                    continue
                except Exception as exc:
                    attempts.append(
                        RepairAttempt(
                            attempt_no=attempt_no,
                            stage="repair_fn",
                            status="execution_error",
                            sql=validated_sql,
                            sanitized_error=f"Repair function failed: {sanitize_db_error(exc)}",
                        )
                    )
                    break
            else:
                break
        else:
            # status in ('ok', 'no_data')
            attempts.append(
                RepairAttempt(
                    attempt_no=attempt_no,
                    sql=validated_sql,
                    stage="ok",
                    status=exec_res.status,
                    sanitized_error=None,
                )
            )
            return exec_res, attempts

    if last_result is None:
        last_result = SqlExecutionResult(
            status="rejected",
            sql=current_sql,
            columns=[],
            rows=[],
            row_count=0,
            error="Maximum repair attempts exceeded without result",
            latency_ms=0.0,
        )

    return last_result, attempts
