"""6-step Text-to-SQL Agent, Self-repair loop, Confidence scoring, and LangGraph Node integration.

Specifications:
- Spec §5 T3 (6-step SQLAgent, LangGraph Integration)
- Review Focus #1: Role-based allowed views filtering before LLM call
- Review Focus #4: Synthetic data warning badge attachment
- TC-T3-04: no_data skips synthesizer and routes to clarify
"""

import time
from typing import Any, Callable
import uuid

from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine

from app.core.config import Settings, get_settings
from app.core.security import get_allowed_views
from db.apply_db import get_ro_engine
from app.knowledge.loader import get_kpi
from app.orchestration.state import ChatState
from app.sql.confidence import score_sql_confidence
from app.sql.context import build_sql_prompt_context
from app.sql.executor import execute_validated_sql
from app.sql.generator import SqlLLMClient, create_sql_llm_client
from app.sql.models import (
    ConfidenceBreakdown,
    RepairAttempt,
    SqlExecutionResult,
    SqlStatus,
)
from app.sql.repair import run_validate_execute_with_repair
from app.sql.validator import validate


class SqlPipelineOutput(BaseModel):
    """Complete structured output from running the 6-step SQLAgent pipeline."""

    status: SqlStatus
    sql: str | None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    confidence: float = 0.0
    confidence_breakdown: ConfidenceBreakdown
    kpi_keys: list[str] = Field(default_factory=list)
    attempts: list[RepairAttempt] = Field(default_factory=list)
    source_query_id: str
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    latency_ms: float = 0.0


def run_sql_pipeline(
    question: str,
    role: str,
    data_profile: str = "real",
    llm_client: SqlLLMClient | None = None,
    engine: Engine | None = None,
    n_candidates: int = 3,
) -> SqlPipelineOutput:
    """Execute the full 6-step Text-to-SQL pipeline.

    Steps:
    1. Context Retrieval (build_sql_prompt_context, RBAC allowed views filter, Golden queries, C1 caveats)
    2. SQL Generation (LLM / heuristic candidate generation)
    3. AST Validation (Single SELECT, allowlist, forbidden funcs, limit)
    4. Read-only Execution (safe execution, timeout, DB error sanitization)
    5. Confidence Verification (similarity + consistency + plausibility)
    6. Self-Repair Loop (capped at 3 attempts if validation/execution fails)
    """
    start_time = time.perf_counter()
    source_query_id = f"sql-{uuid.uuid4().hex[:8]}"
    warnings: list[str] = ["SYNTHETIC_DATA"] if data_profile == "synth" else []

    # Step 1: Context retrieval & RBAC pre-check (Review Focus #1)
    allowed_views = get_allowed_views(role)
    if not allowed_views:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return SqlPipelineOutput(
            status="rejected",
            sql=None,
            columns=[],
            rows=[],
            row_count=0,
            confidence=0.0,
            confidence_breakdown=ConfidenceBreakdown(
                total=0.0,
                passed_mandatory_gate=False,
                golden_similarity=0.0,
                consistency=0.0,
                plausibility=0.0,
            ),
            kpi_keys=[],
            attempts=[],
            source_query_id=source_query_id,
            warnings=warnings,
            error=f"Role '{role}' is not authorized to query any business views.",
            latency_ms=round(elapsed_ms, 2),
        )

    ctx = build_sql_prompt_context(question, role=role, data_profile=data_profile)

    # Check known C1 missing data gaps
    if ctx.known_missing_data_reason:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return SqlPipelineOutput(
            status="no_data",
            sql=None,
            columns=[],
            rows=[],
            row_count=0,
            confidence=0.0,
            confidence_breakdown=ConfidenceBreakdown(
                total=0.0,
                passed_mandatory_gate=True,
                golden_similarity=ctx.golden_matches[0].similarity if ctx.golden_matches else 0.0,
                consistency=0.0,
                plausibility=0.0,
            ),
            kpi_keys=[],
            attempts=[],
            source_query_id=source_query_id,
            warnings=warnings,
            error=ctx.known_missing_data_reason,
            latency_ms=round(elapsed_ms, 2),
        )

    # Step 2: Generation of SQL candidates
    client = llm_client
    if client is None:
        client, _ = create_sql_llm_client("auto")

    candidates = client.generate_candidates(ctx, n=n_candidates)
    if not candidates:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return SqlPipelineOutput(
            status="rejected",
            sql=None,
            columns=[],
            rows=[],
            row_count=0,
            confidence=0.0,
            confidence_breakdown=ConfidenceBreakdown(
                total=0.0,
                passed_mandatory_gate=False,
                golden_similarity=0.0,
                consistency=0.0,
                plausibility=0.0,
            ),
            kpi_keys=[],
            attempts=[],
            source_query_id=source_query_id,
            warnings=warnings,
            error="No SQL candidates generated.",
            latency_ms=round(elapsed_ms, 2),
        )

    primary_draft = candidates[0]
    if primary_draft.out_of_scope_reason:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return SqlPipelineOutput(
            status="no_data",
            sql=primary_draft.sql or None,
            columns=[],
            rows=[],
            row_count=0,
            confidence=0.0,
            confidence_breakdown=ConfidenceBreakdown(
                total=0.0,
                passed_mandatory_gate=True,
                golden_similarity=ctx.golden_matches[0].similarity if ctx.golden_matches else 0.0,
                consistency=0.0,
                plausibility=0.0,
            ),
            kpi_keys=[],
            attempts=[],
            source_query_id=source_query_id,
            warnings=warnings,
            error=primary_draft.out_of_scope_reason,
            latency_ms=round(elapsed_ms, 2),
        )

    # Step 3, 4, 6: Validation, Execution, and Self-Repair Loop
    exec_engine = engine or get_ro_engine(profile=data_profile)

    def execute_fn(sql_to_run: str) -> SqlExecutionResult:
        return execute_validated_sql(sql_to_run, engine=exec_engine)

    def repair_fn(broken_sql: str, sanitized_err: str) -> str:
        return client.repair_sql(ctx, broken_sql, sanitized_err)

    primary_exec_res, attempts = run_validate_execute_with_repair(
        initial_sql=primary_draft.sql,
        allowed_views=ctx.allowed_views,
        execute_fn=execute_fn,
        repair_fn=repair_fn,
        max_attempts=3,
    )

    # Step 5: Verification & Confidence Scoring
    candidate_results: list[SqlExecutionResult] = [primary_exec_res]
    for draft in candidates[1:]:
        if draft.sql and draft.sql.strip():
            try:
                val_sql = validate(draft.sql, allowed_tables=ctx.allowed_views)
                c_res = execute_fn(val_sql)
            except Exception as e:
                c_res = SqlExecutionResult(status="rejected", sql=draft.sql, error=str(e))
            candidate_results.append(c_res)

    golden_sim = ctx.golden_matches[0].similarity if ctx.golden_matches else 0.0

    # Locate relevant KPI definition for plausibility checking
    kpi_def = None
    target_kpi_keys = primary_draft.kpi_keys or ([ctx.golden_matches[0].query.kpi_key] if ctx.golden_matches and ctx.golden_matches[0].query.kpi_key else [])
    if target_kpi_keys:
        kpi_key = target_kpi_keys[0]
        kpi_def = next((k for k in ctx.matched_kpis if k.key == kpi_key), None)
        if not kpi_def:
            try:
                kpi_def = get_kpi(kpi_key)
            except KeyError:
                pass

    confidence_breakdown = score_sql_confidence(
        primary_result=primary_exec_res,
        golden_similarity=golden_sim,
        candidate_results=candidate_results,
        kpi_def=kpi_def,
    )

    # Set kpi_keys strictly when status is ok; when status != ok set kpi_keys = []
    # so that LangGraph routing skips explain, trend, and advise branches
    if primary_exec_res.status == "ok":
        kpi_keys = target_kpi_keys
    else:
        kpi_keys = []

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return SqlPipelineOutput(
        status=primary_exec_res.status,
        sql=primary_exec_res.sql,
        columns=primary_exec_res.columns,
        rows=primary_exec_res.rows,
        row_count=primary_exec_res.row_count,
        confidence=confidence_breakdown.total,
        confidence_breakdown=confidence_breakdown,
        kpi_keys=kpi_keys,
        attempts=attempts,
        source_query_id=source_query_id,
        warnings=warnings,
        error=primary_exec_res.error,
        latency_ms=round(elapsed_ms, 2),
    )


def create_sql_lookup_node(
    llm_client: SqlLLMClient | None = None,
    settings: Settings | None = None,
) -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph node function for sql_lookup."""

    def sql_lookup_node(state: ChatState) -> dict[str, Any]:
        query = state.get("standalone_query") or state.get("query") or ""
        user_info = state.get("user") or {}
        role = user_info.get("role", "ceo")
        data_profile = state.get("data_profile", "real")

        output = run_sql_pipeline(
            question=query,
            role=role,
            data_profile=data_profile,
            llm_client=llm_client,
        )

        updates: dict[str, Any] = {
            "sql": {
                "sql": output.sql,
                "columns": output.columns,
                "rows": output.rows,
                "row_count": output.row_count,
                "status": output.status,
                "confidence": output.confidence,
                "confidence_breakdown": output.confidence_breakdown.model_dump(),
                "source_query_id": output.source_query_id,
                "latency_ms": output.latency_ms,
            },
            "kpi_keys": output.kpi_keys,
            "warnings": output.warnings,
            "trace": [
                {
                    "node": "sql_lookup",
                    "status": output.status,
                    "latency_ms": output.latency_ms,
                    "confidence": output.confidence,
                    "attempts": len(output.attempts),
                }
            ],
        }
        if output.error:
            updates["errors"] = [output.error]

        return updates

    return sql_lookup_node


def confidence_gate_node(state: ChatState, min_confidence: float = 0.45) -> dict[str, Any]:
    """LangGraph node to evaluate confidence and determine if clarification is required.

    Rules:
    - Retains needs_clarification=True if already set.
    - If sql exists in state and (status != 'ok' or confidence < min_confidence),
      sets needs_clarification = True.
    """
    needs_clarification = state.get("needs_clarification", False)
    sql_state = state.get("sql")
    if sql_state:
        status = sql_state.get("status")
        confidence = float(sql_state.get("confidence", 0.0))
        if status != "ok" or confidence < min_confidence:
            needs_clarification = True

    return {"needs_clarification": needs_clarification}
