"""Confidence scoring module for SQL execution results.

Specifications:
- Spec §5 T3 (Confidence Scorer)
- Plan Task 3: T3-SQL Core Confidence Scorer
- Weights: 0.3 Golden Similarity + 0.4 Self-Consistency + 0.3 Result Plausibility
- Mandatory gate: Ast & Exec errors fail gate (total = 0.0)
- No-data queries: plausibility = 0.0
- Plausible range checking from KpiDefinition
"""

from decimal import Decimal
import math
from typing import Any

from app.knowledge.models import KpiDefinition
from app.sql.models import ConfidenceBreakdown, SqlExecutionResult


def _norm_val(v: Any) -> tuple[str, Any]:
    """Normalize a scalar value with 6 significant figures for numeric comparison."""
    if v is None:
        return ("none", None)
    if isinstance(v, bool):
        return ("bool", v)
    if isinstance(v, (int, float, Decimal)):
        try:
            f = float(v)
            if math.isnan(f) or math.isinf(f):
                return ("num_special", str(f))
            return ("num", float(f"{f:.6g}"))
        except (ValueError, OverflowError):
            return ("num_str", str(v))
    return ("str", str(v).strip())


def _normalize_result(res: SqlExecutionResult) -> tuple:
    """Normalize an SqlExecutionResult into an order- and alias-invariant canonical tuple."""
    if res.status != "ok" and res.status != "no_data":
        return ("ERR", res.status)

    if res.status == "no_data" or not res.rows:
        return ("NO_DATA",)

    # For each row, sort normalized values to be invariant to column order/aliases
    norm_rows = []
    for row in res.rows:
        row_tuple = tuple(sorted(_norm_val(v) for v in row.values()))
        norm_rows.append(row_tuple)

    # Sort all rows so result is invariant to row order without ORDER BY
    return tuple(sorted(norm_rows))


def score_sql_confidence(
    primary_result: SqlExecutionResult,
    golden_similarity: float,
    candidate_results: list[SqlExecutionResult] | None = None,
    kpi_def: KpiDefinition | None = None,
) -> ConfidenceBreakdown:
    """Score the confidence of an SQL execution result across multiple signals.

    Formula:
    total = 0.3 * golden_similarity + 0.4 * consistency + 0.3 * plausibility

    Rules:
    1. Mandatory Gate:
       - If status in ('rejected', 'execution_error'), passed_mandatory_gate = False,
         total = 0.0, consistency = 0.0, plausibility = 0.0.
    2. Consistency:
       - Compares candidate execution outputs normalized to 6 significant digits.
       - Ratio of candidates in the pool agreeing with primary_result.
    3. Plausibility:
       - If status == 'no_data': plausibility = 0.0.
       - If status == 'ok':
         - If kpi_def has plausible_range: verified against [min_val, max_val].
           If any value is outside range, plausibility <= 0.2 (0.1).
         - If within range or no range defined: plausibility = 1.0.

    Args:
        primary_result: Execution result of the selected primary query.
        golden_similarity: Cosine similarity to the closest golden query (0.0 to 1.0).
        candidate_results: Optional list of execution results from all candidate queries.
        kpi_def: Optional KpiDefinition with plausible_range.

    Returns:
        ConfidenceBreakdown: Detailed breakdown of the composite confidence score.
    """
    # 1. Mandatory Gate Check
    if primary_result.status in ("rejected", "execution_error"):
        return ConfidenceBreakdown(
            total=0.0,
            passed_mandatory_gate=False,
            golden_similarity=float(golden_similarity),
            consistency=0.0,
            plausibility=0.0,
        )

    passed_mandatory_gate = True

    # 2. Self-Consistency Calculation
    if candidate_results:
        if primary_result in candidate_results or any(c is primary_result for c in candidate_results):
            pool = list(candidate_results)
        else:
            pool = [primary_result] + list(candidate_results)
    else:
        pool = [primary_result]

    primary_norm = _normalize_result(primary_result)
    matches = sum(1 for c in pool if _normalize_result(c) == primary_norm)
    consistency = matches / len(pool) if pool else 1.0

    # 3. Plausibility Calculation
    if primary_result.status == "no_data":
        plausibility = 0.0
    else:
        plausibility = 1.0
        numeric_vals: list[float] = []
        for row in primary_result.rows:
            for v in row.values():
                if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
                    try:
                        f = float(v)
                        numeric_vals.append(f)
                    except (ValueError, TypeError):
                        pass

        if any(math.isnan(v) or math.isinf(v) for v in numeric_vals):
            plausibility = 0.0
        elif kpi_def is not None and kpi_def.plausible_range is not None:
            min_val, max_val = kpi_def.plausible_range
            if numeric_vals and any(v < min_val or v > max_val for v in numeric_vals):
                plausibility = 0.1
            else:
                plausibility = 1.0

    # 4. Total Composite Score
    total = 0.3 * golden_similarity + 0.4 * consistency + 0.3 * plausibility
    total = max(0.0, min(1.0, total))

    return ConfidenceBreakdown(
        total=total,
        passed_mandatory_gate=passed_mandatory_gate,
        golden_similarity=float(golden_similarity),
        consistency=float(consistency),
        plausibility=float(plausibility),
    )
