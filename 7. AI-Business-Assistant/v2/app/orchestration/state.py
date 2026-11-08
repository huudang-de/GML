"""ChatState and Intent definitions for LangGraph orchestration."""

import operator
from typing import Annotated, Literal, TypedDict

Intent = Literal["sql_only", "rag_only", "both", "alert", "blocked"]


class ChatState(TypedDict, total=False):
    request_id: str
    user: dict  # {"id": ..., "role": "ceo" | "ke_toan_truong" | ...}
    session_id: str
    query: str  # câu hỏi gốc
    standalone_query: str  # câu hỏi độc lập sau follow-up
    intent: Intent
    sql: dict  # {"sql", "columns", "rows", "row_count", "status", "confidence"}
    rag: dict  # {"chunks", "sources", "grounding_ok"}
    kpi_keys: list[str]
    explanation: dict
    trend: dict
    advice: list[dict]
    needs_clarification: bool
    answer: dict
    errors: Annotated[list[str], operator.add]  # nhiều node cùng ghi được
    trace: Annotated[list[dict], operator.add]  # nhật ký thực thi các node
