"""SQL parsing, AST validation, execution, self-repair, and confidence scoring module."""

from app.sql.confidence import score_sql_confidence
from app.sql.executor import execute_validated_sql
from app.sql.models import (
    ConfidenceBreakdown,
    RepairAttempt,
    SqlDraft,
    SqlExecutionResult,
    SqlStatus,
)
from app.sql.repair import run_validate_execute_with_repair
from app.sql.validator import FORBIDDEN_FUNCS, validate, validate_for_role

__all__ = [
    "ConfidenceBreakdown",
    "FORBIDDEN_FUNCS",
    "RepairAttempt",
    "SqlDraft",
    "SqlExecutionResult",
    "SqlStatus",
    "execute_validated_sql",
    "run_validate_execute_with_repair",
    "score_sql_confidence",
    "validate",
    "validate_for_role",
]
