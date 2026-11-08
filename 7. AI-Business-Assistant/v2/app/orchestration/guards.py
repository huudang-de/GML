"""Safety guards for LangGraph input inspection and output sanitization.

Specifications:
- Spec §5 T4, §11.7
- TC-T4-04: Block destructive DDL/DML, prompt injection, and RBAC domain violations
- TC-T4-05: Neutralize prompt injection and internal credentials/schema in output
"""

from collections.abc import Callable
import re
from typing import Any

from app.agents.intent import classify_intent_heuristic
from app.core.errors import sanitize_db_error
from app.orchestration.state import ChatState


def create_guard_input_node() -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph input guard node to validate queries before agent invocation."""

    def guard_input_node(state: ChatState) -> dict[str, Any]:
        query = state.get("query", "")
        user = state.get("user") or {}
        role = user.get("role", "ceo")

        intent = classify_intent_heuristic(query=query, role=role)
        if intent == "blocked":
            reason = f"Truy vấn bị từ chối do thao tác không an toàn, tiêm mã (injection), hoặc vượt quyền hạn vai trò '{role}'."
            return {
                "intent": "blocked",
                "errors": [reason],
                "trace": [{"node": "guard_input", "status": "blocked", "reason": reason}],
            }

        return {
            "trace": [{"node": "guard_input", "status": "ok"}],
        }

    return guard_input_node


def sanitize_text(text: str) -> tuple[str, bool]:
    """Sanitize database URIs, passwords, credentials, and internal silver schema references."""
    sanitized = text
    modified = False

    # 1. Sanitize postgresql:// URI patterns
    if "postgresql://" in sanitized:
        sanitized = re.sub(
            r"postgresql(?:\+[a-zA-Z0-9_]+)?://[^\s'\"]+",
            "[REDACTED_DATABASE_URI]",
            sanitized,
        )
        modified = True

    # 2. Sanitize credential patterns user:password@host
    if re.search(r"[a-zA-Z0-9_\-\.]+:[^@\s]+@[a-zA-Z0-9_\-\.]+", sanitized):
        sanitized = re.sub(
            r"[a-zA-Z0-9_\-\.]+:[^@\s]+@",
            "[REDACTED_CREDENTIALS]@",
            sanitized,
        )
        modified = True

    # 3. Sanitize internal silver. schema references
    if "silver." in sanitized:
        sanitized = re.sub(r"silver\.[a-zA-Z0-9_]+", "[REDACTED_INTERNAL_SCHEMA]", sanitized)
        modified = True

    # 4. Standard database error sanitization
    standard_sanitized = sanitize_db_error(sanitized)
    if standard_sanitized != sanitized:
        sanitized = standard_sanitized
        modified = True

    return sanitized, modified


def create_guard_output_node() -> Callable[[ChatState], dict[str, Any]]:
    """Create a LangGraph output guard node to sanitize answers and enforce synthetic markers."""

    def guard_output_node(state: ChatState) -> dict[str, Any]:
        answer = dict(state.get("answer") or {})
        explanation = dict(state.get("explanation") or {})
        warnings = list(dict.fromkeys(list(state.get("warnings") or []) + list(answer.get("warnings") or [])))
        data_profile = state.get("data_profile", "real")

        was_sanitized = False

        # Sanitize answer summary
        if "summary" in answer and isinstance(answer["summary"], str):
            clean_summary, changed = sanitize_text(answer["summary"])
            answer["summary"] = clean_summary
            if changed:
                was_sanitized = True

        # Sanitize explanation narrative
        if "narrative" in explanation and isinstance(explanation["narrative"], str):
            clean_narrative, changed = sanitize_text(explanation["narrative"])
            explanation["narrative"] = clean_narrative
            if changed:
                was_sanitized = True

        if was_sanitized and "OUTPUT_SANITIZED" not in warnings:
            warnings.append("OUTPUT_SANITIZED")

        # Guarantee SYNTHETIC_DATA warning on synth profile
        if data_profile == "synth" and "SYNTHETIC_DATA" not in warnings:
            warnings.append("SYNTHETIC_DATA")

        answer["warnings"] = list(dict.fromkeys(warnings))

        return {
            "answer": answer,
            "explanation": explanation,
            "warnings": warnings,
            "trace": [{"node": "guard_output", "status": "ok"}],
        }

    return guard_output_node
