"""Audit log writer for tracking API and database query activities.

Specifications:
- Review Focus #3: Audit log records execution metadata and sanitized SQL, never result numbers.
- Spec §5 T5, §11.7
"""

import logging
import re
from typing import Any
import sqlglot
from sqlglot import exp
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.core.errors import sanitize_db_error
from app.orchestration.guards import sanitize_text

logger = logging.getLogger(__name__)


def extract_views_from_sql(sql: str) -> list[str]:
    """Extract ai_v_* view names referenced in an SQL query using AST parsing."""
    if not sql or not sql.strip():
        return []

    views = set()
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
        for table_node in tree.find_all(exp.Table):
            t_name = (table_node.name or "").lower()
            if t_name.startswith("ai_v_"):
                views.add(t_name)
    except Exception:
        # Fallback to regex extraction if AST parsing fails
        matches = re.findall(r"\b(ai_v_[a-zA-Z0-9_]+)\b", sql, re.IGNORECASE)
        for m in matches:
            views.add(m.lower())

    return sorted(views)


def write_audit_log(
    engine: Engine,
    user_id: str,
    role: str,
    request_id: str,
    query: str | None = None,
    sql_executed: str | None = None,
    views_accessed: list[str] | None = None,
    execution_time_ms: float = 0.0,
) -> None:
    """Record query execution into app.audit_log.

    Guarantees:
    1. Credentials, URIs, and raw silver schemas in query/sql are sanitized.
    2. Zero data rows or numeric calculation results are stored.
    3. Failure in audit logging does not crash the calling workflow.
    """
    try:
        sanitized_query = None
        if query:
            clean_q, _ = sanitize_text(query)
            sanitized_query = sanitize_db_error(clean_q)

        sanitized_sql = None
        if sql_executed:
            clean_sql, _ = sanitize_text(sql_executed)
            sanitized_sql = sanitize_db_error(clean_sql)

        final_views = list(views_accessed) if views_accessed is not None else []
        if sanitized_sql and not final_views:
            final_views = extract_views_from_sql(sanitized_sql)

        stmt = sa.text("""
            INSERT INTO app.audit_log (
                user_id, role, query, sql_executed, views_accessed, request_id, execution_time_ms, created_at
            ) VALUES (
                :user_id, :role, :query, :sql_executed, :views_accessed, :request_id, :execution_time_ms, now()
            );
        """)

        with engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "user_id": user_id,
                    "role": role,
                    "query": sanitized_query,
                    "sql_executed": sanitized_sql,
                    "views_accessed": final_views,
                    "request_id": request_id,
                    "execution_time_ms": float(execution_time_ms),
                },
            )
    except Exception as e:
        logger.error(f"Failed to write audit log for request_id={request_id}: {e}", exc_info=True)
