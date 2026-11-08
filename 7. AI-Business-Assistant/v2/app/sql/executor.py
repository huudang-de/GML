"""Read-only SQL execution engine with type conversion, error sanitization, and no_data classification.

Specifications:
- Spec §5 T3 (Read-only SQL Executor)
- Plan Task 3: T3-SQL Core Executor
- Review Focus #2: Aggregate query with all NULL values treated as no_data
- Review Focus #5: DB exception sanitization via sanitize_db_error
"""

from datetime import date, datetime
from decimal import Decimal
import time
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.core.errors import sanitize_db_error
from app.sql.models import SqlExecutionResult
from db.apply_db import get_ro_engine


def _serialize_value(val: Any) -> Any:
    """Serialize database types to JSON/Python primitive equivalents."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def execute_validated_sql(
    sql: str,
    profile: str = "real",
    engine: Engine | None = None,
    max_rows: int = 1000,
) -> SqlExecutionResult:
    """Execute a validated read-only SQL query against PostgreSQL.

    Enforces:
    1. Read-only connection profile (gml_ai_ro).
    2. Conversion of Decimal -> float, date/datetime -> ISO string.
    3. Classification:
       - 'no_data': 0 rows returned OR all column values across all rows are None
         (Review Focus #2: handles PostgreSQL SUM/AVG over empty sets returning [(None,)]).
       - 'ok': Rows returned with at least one non-None value.
       - 'execution_error': Any database exception, sanitized with sanitize_db_error().

    Args:
        sql: Validated SQL statement.
        profile: Database profile ('real' or 'synth').
        engine: Optional pre-configured SQLAlchemy engine (useful for testing).
        max_rows: Maximum rows to fetch (default: 1000).

    Returns:
        SqlExecutionResult: Structured execution output.
    """
    t0 = time.perf_counter()
    target_engine = engine or get_ro_engine(profile=profile)

    try:
        with target_engine.connect() as conn:
            cursor_res = conn.execute(sa.text(sql))
            returns_rows = getattr(cursor_res, "returns_rows", True)
            if not returns_rows:
                latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                return SqlExecutionResult(
                    status="no_data",
                    sql=sql,
                    columns=[],
                    rows=[],
                    row_count=0,
                    error=None,
                    latency_ms=latency_ms,
                )

            columns: list[str] = list(cursor_res.keys()) if hasattr(cursor_res, "keys") else []
            if hasattr(cursor_res, "fetchmany"):
                raw_rows = cursor_res.fetchmany(max_rows)
            elif hasattr(cursor_res, "fetchall"):
                raw_rows = cursor_res.fetchall()[:max_rows]
            else:
                raw_rows = list(cursor_res)[:max_rows]

            rows: list[dict[str, Any]] = []
            for raw_row in raw_rows:
                if hasattr(raw_row, "_mapping"):
                    mapping = raw_row._mapping
                    if not columns:
                        columns = list(mapping.keys())
                    row_dict = {col: _serialize_value(mapping[col]) for col in columns}
                elif isinstance(raw_row, dict):
                    if not columns:
                        columns = list(raw_row.keys())
                    row_dict = {col: _serialize_value(raw_row.get(col)) for col in columns}
                elif isinstance(raw_row, (tuple, list)):
                    if not columns:
                        columns = [f"col_{i}" for i in range(len(raw_row))]
                    row_dict = {col: _serialize_value(val) for col, val in zip(columns, raw_row)}
                else:
                    row_dict = {col: _serialize_value(getattr(raw_row, col, None)) for col in columns}
                rows.append(row_dict)

            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            # Review Focus #2:
            # Check for empty result OR all-null values (e.g. SELECT SUM(...) WHERE 1=0 returning [{'sum': None}])
            is_empty = len(rows) == 0
            is_all_null = len(rows) > 0 and all(
                all(v is None for v in row.values()) for row in rows
            )

            if is_empty or is_all_null:
                return SqlExecutionResult(
                    status="no_data",
                    sql=sql,
                    columns=columns,
                    rows=[],
                    row_count=0,
                    error=None,
                    latency_ms=latency_ms,
                )

            return SqlExecutionResult(
                status="ok",
                sql=sql,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                error=None,
                latency_ms=latency_ms,
            )

    except Exception as exc:
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        sanitized_error = sanitize_db_error(exc)
        return SqlExecutionResult(
            status="execution_error",
            sql=sql,
            columns=[],
            rows=[],
            row_count=0,
            error=sanitized_error,
            latency_ms=latency_ms,
        )
