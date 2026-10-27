"""Typed, serializable contracts between the SQL and response layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


SQLStatus = Literal["ok", "no_data", "execution_error"]


@dataclass
class SQLExecution:
    status: SQLStatus
    rows: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_state(self) -> dict[str, Any]:
        return {
            "sql_status": self.status,
            "data": self.rows,
            "row_count": len(self.rows),
            "sql_error": self.error or "",
            # Kept only for backwards-compatible prompt/log rendering.
            "sql_result": str(self.rows),
        }
