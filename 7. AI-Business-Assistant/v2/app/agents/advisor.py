"""DecisionAdvisor Agent for Business Rule Action Recommendations and CFO SOP Playbooks.

Specifications:
- Spec Phần II §6 (Agent Architecture) & §5 T3 (DecisionAdvisor)
- TC-T3-11: Strict allowlist filtering out any unauthorized LLM actions
- TC-T3-12: Mandatory authority disclaimer enforcement on all advice
- CFO Playbooks (SOP-01..04) integration with authority role mapping
"""

import re
from typing import Any, Callable, Literal
import unicodedata

from app.agents.llm_text import TextLLMClient
from app.agents.models import Advice
from app.knowledge.loader import (
    get_business_actions,
    get_kpi,
    load_business_rules,
    load_cfo_playbooks,
    load_kpis,
    match_cfo_playbooks,
)
from app.orchestration.state import ChatState

MANDATORY_DISCLAIMER = "Gợi ý tham khảo từ quy tắc nghiệp vụ, cần người có thẩm quyền quyết định"


def _normalize_text(text: str) -> str:
    """Normalize text by lowercasing, stripping punctuation, and normalizing unicode."""
    text = unicodedata.normalize("NFC", text or "").lower().strip()
    text = re.sub(r"[.,;:!?'\"\-–—*]+", " ", text)
    return " ".join(text.split())


def check_threshold_condition(value: float, expr: str) -> bool:
    """Evaluate a numeric value against a threshold expression string."""
    expr = expr.strip()
    try:
        if expr.startswith(">="):
            target = float(expr[2:].strip().replace(",", "."))
            return value >= target
        elif expr.startswith("<="):
            target = float(expr[2:].strip().replace(",", "."))
            return value <= target
        elif expr.startswith(">"):
            target = float(expr[1:].strip().replace(",", "."))
            return value > target
        elif expr.startswith("<"):
            target = float(expr[1:].strip().replace(",", "."))
            return value < target
        elif expr.startswith("=="):
            target = float(expr[2:].strip().replace(",", "."))
            return value == target
    except ValueError:
        return False
    return False


def evaluate_kpi_threshold_level(
    kpi_key: str,
    value: float,
) -> Literal["nghiem_trong", "canh_bao"] | None:
    """Evaluate a KPI value against defined thresholds, checking nghiem_trong before canh_bao."""
    thresholds: dict[str, str] = {}
    kpis = load_kpis()

    if kpi_key in kpis:
        kpi_def = kpis[kpi_key]
        thresholds = kpi_def.nguong or {}
    elif kpi_key == "current_ratio":
        thresholds = {"canh_bao": "< 1.2", "nghiem_trong": "< 1.0"}

    if not thresholds:
        return None

    nt_expr = thresholds.get("nghiem_trong")
    cb_expr = thresholds.get("canh_bao")

    if nt_expr and check_threshold_condition(value, nt_expr):
        return "nghiem_trong"
    if cb_expr and check_threshold_condition(value, cb_expr):
        return "canh_bao"

    return None


def filter_approved_actions(
    candidate_actions: list[str],
    approved_actions: list[str],
) -> tuple[list[str], bool]:
    """Filter candidate actions against approved operational actions list.

    TC-T3-11: Candidate actions from LLM are strictly validated. Only actions
    that match an approved action (ignoring case, whitespace, and punctuation)
    are retained. Any unauthorized action triggers has_unapproved = True.
    """
    normalized_approved = {_normalize_text(act): act for act in approved_actions}
    filtered: list[str] = []
    has_unapproved = False

    for cand in candidate_actions:
        cand_clean = cand.strip()
        if not cand_clean:
            continue
        norm_cand = _normalize_text(cand_clean)
        if norm_cand in normalized_approved:
            canonical = normalized_approved[norm_cand]
            if canonical not in filtered:
                filtered.append(canonical)
        else:
            has_unapproved = True

    return filtered, has_unapproved


def _extract_candidate_actions(text: str) -> list[str]:
    """Parse bullet points or numbered lines from LLM response text."""
    lines = text.strip().splitlines()
    candidates: list[str] = []
    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        # Remove common bullet prefixes like '- ', '* ', '1. ', '2) '
        cleaned = re.sub(r"^[-*•\d.)\]\s]+", "", cleaned).strip()
        if cleaned:
            candidates.append(cleaned)
    return candidates


def run_advisor(
    kpi_keys: list[str],
    sql_state: dict[str, Any] | None = None,
    trend_state: dict[str, Any] | None = None,
    llm_client: TextLLMClient | None = None,
) -> tuple[list[Advice], list[str]]:
    """Synthesize prescriptive recommendations from business rules and CFO SOP playbooks.

    Specifications:
    - TC-T3-11: Filter unauthorized actions, emitting 'UNAPPROVED_ACTION_BLOCKED' warning.
    - TC-T3-12: Enforce mandatory authority disclaimer on all Advice objects.
    - CFO Playbooks (SOP-01..04) triggers based on operational KPI metrics.
    """
    advices: list[Advice] = []
    warnings: list[str] = []

    # Step 1: Collect KPI values from sql_state and trend_state
    kpi_values: dict[str, float] = {}

    if sql_state:
        rows = sql_state.get("rows", [])
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    for k, v in row.items():
                        if isinstance(v, (int, float)) and not isinstance(v, bool):
                            kpi_values[k] = float(v)

    if trend_state:
        trend_kpi = trend_state.get("kpi_key")
        series = trend_state.get("series", [])
        if series and isinstance(series, list):
            last_pt = series[-1]
            if isinstance(last_pt, dict) and "value" in last_pt:
                try:
                    kpi_values[trend_kpi] = float(last_pt["value"])
                except (ValueError, TypeError):
                    pass

    # If kpi_keys are specified and have single numeric value in sql_state
    if sql_state and kpi_keys:
        primary = kpi_keys[0]
        if primary not in kpi_values and "rows" in sql_state:
            rows = sql_state["rows"]
            if rows and isinstance(rows[0], dict) and len(rows[0]) == 1:
                val = next(iter(rows[0].values()))
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    kpi_values[primary] = float(val)

    # Step 2: Evaluate business rules for specified KPI keys
    rules_cfg = load_business_rules()

    for kpi_key in kpi_keys:
        val = kpi_values.get(kpi_key)
        if val is None:
            continue

        level = evaluate_kpi_threshold_level(kpi_key, val)
        if level is None:
            continue

        if kpi_key not in rules_cfg or level not in rules_cfg[kpi_key]:
            continue

        rule_data = get_business_actions(kpi_key, level)
        approved_actions = rule_data.get("actions", [])
        authority_role = rule_data.get("authority_role", "ceo")
        disclaimer = rule_data.get("disclaimer", MANDATORY_DISCLAIMER)

        actions = approved_actions

        # If LLM client is provided, validate candidate actions against approved allowlist (TC-T3-11)
        if llm_client is not None:
            prompt = (
                f"Đề xuất hành động cho chỉ số {kpi_key} ở mức {level}.\n"
                f"Danh sách hành động cho phép:\n"
                + "\n".join(f"- {a}" for a in approved_actions)
            )
            try:
                llm_response = llm_client.generate_text(
                    system_prompt="Bạn là cố vấn tài chính Ban Giám Đốc GML.",
                    user_prompt=prompt,
                )
                candidates = _extract_candidate_actions(llm_response)
                filtered, has_unapproved = filter_approved_actions(candidates, approved_actions)
                if has_unapproved:
                    warnings.append("UNAPPROVED_ACTION_BLOCKED")
                if filtered:
                    actions = filtered
            except Exception:
                actions = approved_actions

        advices.append(
            Advice(
                kpi_key=kpi_key,
                level=level,
                actions=actions,
                authority_role=authority_role,
                disclaimer=disclaimer,
            )
        )

    # Step 3: Match CFO playbooks (SOP-01..04)
    matched_playbooks = match_cfo_playbooks(kpi_values)
    for pb in matched_playbooks:
        pb_id = pb.get("id", "SOP")
        pb_name = pb.get("name", "Playbook")
        pb_level = pb.get("level", "nghiem_trong")
        pb_role = pb.get("authority_role", "ceo")
        pb_actions = pb.get("actions", [])
        pb_disclaimer = pb.get("disclaimer", MANDATORY_DISCLAIMER)

        advices.append(
            Advice(
                kpi_key=f"{pb_id}: {pb_name}",
                level=pb_level,
                actions=pb_actions,
                authority_role=pb_role,
                disclaimer=pb_disclaimer,
            )
        )

    return advices, warnings


def create_advise_node(
    llm_client: TextLLMClient | None = None,
) -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph node function for decision advising.

    Review Focus #2: Node writes ONLY a subset of {'advice', 'warnings', 'trace', 'errors'}.
    """

    def advise_node(state: ChatState) -> dict[str, Any]:
        kpi_keys = state.get("kpi_keys", [])
        sql_state = state.get("sql")
        trend_state = state.get("trend")

        advices, warnings = run_advisor(
            kpi_keys=kpi_keys,
            sql_state=sql_state,
            trend_state=trend_state,
            llm_client=llm_client,
        )

        updates: dict[str, Any] = {
            "advice": [a.model_dump() for a in advices],
            "warnings": warnings,
            "trace": [
                {
                    "node": "advisor",
                    "kpi_keys": kpi_keys,
                    "advice_count": len(advices),
                }
            ],
        }
        return updates

    return advise_node
