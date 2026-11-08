"""AST SQL Validator and Role-Based Allowlist Enforcement using sqlglot.

Adheres to:
- Spec §5 T3 (Safe AST SQL Verification)
- Spec §6.2 (Pipeline 6 bước: Bước 4 Kiểm tra an toàn SQL)
- Spec §11.9 (Role-to-View Authorization Matrix)
- TC-T3-01: Blocks destructive statements (DML/DDL), multi-statements, forbidden funcs
- TC-T3-02: Enforces role-based views allowlist & blocks direct access to silver/system schemas
- TC-T3-03: Enforces and caps LIMIT (default 1000)
"""

import re
from typing import Set

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from app.core.errors import SqlRejected
from app.core.security import get_allowed_views

# Spec §5 T3: Forbidden postgres administrative / filesystem functions
FORBIDDEN_FUNCS: Set[str] = {
    "pg_sleep",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "pg_stat_file",
    "lo_import",
    "lo_export",
    "dblink",
    "dblink_exec",
    "query_to_xml",
}

# Review Focus #3: Nodes that must never appear in query AST at any depth
FORBIDDEN_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Command,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Grant,
    exp.Revoke,
    exp.Into,
    exp.Lock,
)

# Regex pattern for forbidden functions on raw SQL string (defense in depth)
FORBIDDEN_FUNCS_RE = re.compile(
    r"\b(" + "|".join(re.escape(fn) for fn in sorted(FORBIDDEN_FUNCS)) + r")\b",
    re.IGNORECASE,
)


def _is_select_or_union(node: exp.Expression) -> bool:
    """Recursively check whether the root node is a SELECT or a UNION of SELECTs."""
    if isinstance(node, exp.Select):
        return True
    if isinstance(node, exp.Union):
        return _is_select_or_union(node.this) and _is_select_or_union(node.expression)
    return False


def validate(sql: str, allowed_tables: Set[str], max_rows: int = 1000) -> str:
    """Validate and sanitize an SQL query using sqlglot AST analysis.

    Enforces:
    1. Single non-empty SQL statement.
    2. Read-only SELECT/UNION statements only.
    3. Complete absence of DML/DDL/transaction/lock operations at any depth.
    4. Table and schema boundaries: only allowed tables in 'ai_views' schema.
    5. Absence of forbidden administrative/filesystem/injection functions.
    6. Presence and cap on outer LIMIT clause (capped to max_rows).

    Args:
        sql: Raw SQL query string.
        allowed_tables: Set of view/table names permitted for the caller.
        max_rows: Maximum rows allowed in outer LIMIT clause (default: 1000).

    Returns:
        str: Validated and sanitized SQL string formatted for postgres dialect.

    Raises:
        SqlRejected: If the query violates any security rule or AST policy.
    """
    if not sql or not sql.strip():
        raise SqlRejected("SQL rỗng hoặc không hợp lệ")

    # 1. Regex defense-in-depth scan for forbidden functions on raw SQL
    match = FORBIDDEN_FUNCS_RE.search(sql)
    if match:
        raise SqlRejected(f"Hàm không được phép: {match.group(0)}")

    # 2. Parse SQL using sqlglot postgres dialect
    try:
        parsed_trees = sqlglot.parse(sql, read="postgres")
    except SqlglotError as e:
        raise SqlRejected(f"Lỗi cú pháp SQL: {e}") from e
    except Exception as e:
        raise SqlRejected(f"Lỗi cú pháp SQL: {e}") from e

    # Single statement check
    trees = [t for t in parsed_trees if t is not None]
    if len(trees) == 0:
        raise SqlRejected("SQL rỗng hoặc không hợp lệ")
    if len(trees) > 1:
        raise SqlRejected("Chỉ cho phép một câu lệnh SQL duy nhất")

    tree = trees[0]

    # 3. Only SELECT / UNION allowed as root statement
    if not _is_select_or_union(tree):
        key = getattr(tree, "key", str(type(tree).__name__))
        raise SqlRejected(f"Chỉ cho phép câu lệnh SELECT (nhận được: {key})")

    # 4. Review Focus #3: Check for destructive / DML / DDL nodes at ANY depth (CTE/subqueries)
    for node in tree.find_all(FORBIDDEN_NODES):
        key = getattr(node, "key", str(type(node).__name__))
        raise SqlRejected(f"Thao tác không được phép: {key}")

    # 5. Check for forbidden functions in AST
    for f in tree.find_all(exp.Func):
        fname = (getattr(f, "name", "") or f.key or "").lower()
        if fname in FORBIDDEN_FUNCS:
            raise SqlRejected(f"Hàm không được phép: {fname}")

    # 6. Review Focus #1: Schema and Table allowlist validation
    norm_allowed_tables = {tbl.strip().lower().split(".")[-1] for tbl in allowed_tables}
    cte_names = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE) if c.alias_or_name}

    for t in tree.find_all(exp.Table):
        table_name = t.name.lower() if t.name else ""
        schema_name = t.db.lower() if t.db else ""
        catalog_name = t.catalog.lower() if t.catalog else ""

        # Disallow catalog references
        if catalog_name:
            raise SqlRejected(f"Catalog không được phép: {catalog_name}")

        # If referencing an internal CTE defined in this query
        if table_name and table_name in cte_names and schema_name == "":
            continue

        # Enforce schema boundary: disallow foreign schemas (silver, pg_catalog, information_schema, etc.)
        if schema_name != "" and schema_name != "ai_views":
            raise SqlRejected(
                f"Schema không được phép: {schema_name}. Chỉ được phép truy vấn schema 'ai_views'"
            )

        # Disallow empty table names or tables not in the allowlist
        if not table_name or table_name not in norm_allowed_tables:
            raise SqlRejected(f"Bảng không được phép: {table_name}")

    # 7. Review Focus #2: Enforce & cap LIMIT clause
    limit_node = tree.args.get("limit")
    if limit_node is None:
        tree = tree.limit(max_rows)
    else:
        try:
            val_str = str(limit_node.expression)
            val = int(val_str)
            if val > max_rows or val <= 0:
                tree = tree.limit(max_rows)
        except (ValueError, TypeError, AttributeError):
            tree = tree.limit(max_rows)

    return tree.sql(dialect="postgres")


def validate_for_role(sql: str, role: str, max_rows: int = 1000) -> str:
    """Validate an SQL query according to the permissions of a user role.

    Args:
        sql: Raw SQL query string.
        role: User role string (e.g. 'ceo', 'ke_toan_truong', 'quan_ly_kho').
        max_rows: Maximum rows allowed (default: 1000).

    Returns:
        str: Validated and sanitized SQL string.

    Raises:
        SqlRejected: If the role has no table permissions or the query violates rules.
    """
    allowed_views = get_allowed_views(role)
    if not allowed_views:
        raise SqlRejected(f"Vai trò '{role}' không có quyền truy vấn bất kỳ bảng dữ liệu nào")

    return validate(sql, allowed_tables=allowed_views, max_rows=max_rows)
