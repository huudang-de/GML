"""Text-to-SQL generation clients and factory.

Supports:
- GeminiSqlLLMClient (Google Gemini via ChatGoogleGenerativeAI)
- OllamaSqlLLMClient (Local Ollama LLM endpoint)
- HeuristicGoldenSqlClient (Deterministic Golden-match + parameter extractor for offline evaluation TC-T8-01)
- MockSqlLLMClient (Test harness fixture)
- create_sql_llm_client factory with auto-detection
"""

import json
import logging
import re
from typing import Any, Callable, Protocol, Sequence
import urllib.request
import urllib.error

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.sql.context import SqlPromptContext
from app.sql.models import SqlDraft

logger = logging.getLogger(__name__)


class SqlLLMClient(Protocol):
    """Protocol defining the interface for SQL generation and self-repair LLM clients."""

    def generate_candidates(self, ctx: SqlPromptContext, n: int = 3) -> list[SqlDraft]:
        """Generate n candidate SQL queries with explanations and optional KPI keys."""
        ...

    def repair_sql(self, ctx: SqlPromptContext, broken_sql: str, sanitized_error: str) -> str:
        """Repair a failed SQL statement given sanitized AST or execution errors."""
        ...


class MockSqlLLMClient:
    """Mock SQL LLM client for unit and integration testing."""

    def __init__(
        self,
        candidates: list[SqlDraft] | None = None,
        generator_fn: Callable[[SqlPromptContext, int], list[SqlDraft]] | None = None,
        repair_fn: Callable[[SqlPromptContext, str, str], str] | None = None,
    ) -> None:
        self.candidates = candidates or [SqlDraft(sql="SELECT 1;")]
        self.generator_fn = generator_fn
        self.repair_fn = repair_fn
        self.call_count = 0
        self.repair_call_count = 0

    def generate_candidates(self, ctx: SqlPromptContext, n: int = 3) -> list[SqlDraft]:
        self.call_count += 1
        if self.generator_fn:
            return self.generator_fn(ctx, n)
        return self.candidates[:n] if len(self.candidates) >= n else self.candidates

    def repair_sql(self, ctx: SqlPromptContext, broken_sql: str, sanitized_error: str) -> str:
        self.repair_call_count += 1
        if self.repair_fn:
            return self.repair_fn(ctx, broken_sql, sanitized_error)
        return broken_sql


class HeuristicGoldenSqlClient:
    """Deterministic SQL generator for offline testing and evaluation (TC-T8-01).

    Leverages Golden Query Bank matching, C1 caveats detection, and schema rules.
    """

    def generate_candidates(self, ctx: SqlPromptContext, n: int = 3) -> list[SqlDraft]:
        # 1. Check known missing data / out of scope (C1 caveats)
        if ctx.known_missing_data_reason:
            return [
                SqlDraft(
                    sql="",
                    explanation_short=ctx.known_missing_data_reason,
                    out_of_scope_reason=ctx.known_missing_data_reason,
                    kpi_keys=[],
                )
            ]

        # 2. Check if user role has permitted views
        if not ctx.allowed_views:
            return [
                SqlDraft(
                    sql="",
                    explanation_short=f"Role '{ctx.role}' does not have permission to query views.",
                    out_of_scope_reason="RBAC_DENIED",
                    kpi_keys=[],
                )
            ]

        # 3. Match against Golden Query Bank
        if ctx.golden_matches:
            top_match = ctx.golden_matches[0]
            base_sql = top_match.query.sql_text.strip()
            kpi_key = top_match.query.kpi_key
            kpi_keys = [kpi_key] if kpi_key else []

            candidates: list[SqlDraft] = []
            for i in range(max(1, n)):
                # Return consistent candidates
                candidates.append(
                    SqlDraft(
                        sql=base_sql,
                        explanation_short=f"Khớp Golden Query {top_match.query.id}: {top_match.query.question_vi}",
                        kpi_keys=kpi_keys,
                    )
                )
            return candidates

        # 4. Fallback if no golden match
        return [
            SqlDraft(
                sql="SELECT 1;",
                explanation_short="Fallback query without golden match",
                kpi_keys=[],
            )
        ]

    def repair_sql(self, ctx: SqlPromptContext, broken_sql: str, sanitized_error: str) -> str:
        # Check if silver. schema was mistakenly referenced
        if "silver." in broken_sql:
            return broken_sql.replace("silver.", "ai_views.")

        # If top golden match exists, fallback to its known good SQL
        if ctx.golden_matches:
            return ctx.golden_matches[0].query.sql_text.strip()

        return broken_sql


class GeminiSqlLLMClient:
    """Google Gemini SQL generator using structured prompting."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate_candidates(self, ctx: SqlPromptContext, n: int = 3) -> list[SqlDraft]:
        if ctx.known_missing_data_reason:
            return [
                SqlDraft(
                    sql="",
                    explanation_short=ctx.known_missing_data_reason,
                    out_of_scope_reason=ctx.known_missing_data_reason,
                )
            ]

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = ChatGoogleGenerativeAI(
                model=self.settings.llm_model,
                google_api_key=self.settings.google_api_key,
                temperature=0.0,
            )

            system_prompt = (
                "Bạn là chuyên gia cơ sở dữ liệu và kế toán của Công ty Cổ phần Gỗ Minh Long.\n"
                "Nhiệm vụ: Viết truy vấn PostgreSQL (schema ai_views) để trả lời câu hỏi của người dùng.\n"
                f"Người dùng có vai trò: {ctx.role}.\n"
                f"Ngày chốt số liệu (AS_OF_DATE): {ctx.as_of_date.isoformat()}.\n"
                "QUY TẮC BẮT BUỘC:\n"
                "1. Chỉ truy vấn các view trong schema ai_views được liệt kê dưới đây.\n"
                "2. Chỉ tạo câu lệnh SELECT đơn lẻ, không dùng INSERT/UPDATE/DELETE/DROP.\n"
                "3. Luôn trả lời bằng định dạng JSON có cấu trúc là một mảng gồm các đối tượng có các trường: "
                "'sql' (chuỗi), 'explanation_short' (chuỗi giải thích ngắn gọn), 'kpi_keys' (mảng chuỗi các KPI liên quan).\n\n"
                f"DANH MỤC VIEWS:\n{ctx.catalog_markdown}\n\n"
                f"LƯU Ý DỮ LIỆU C1:\n" + "\n".join(f"- {c}" for c in ctx.c1_caveats) + "\n"
            )

            human_prompt = f"Câu hỏi: {ctx.question}\nHãy sinh {n} phương án SQL."
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
            response = llm.invoke(messages)
            content = str(response.content)

            # Extract JSON block
            candidates = self._parse_json_candidates(content)
            if candidates:
                return candidates[:n]
        except Exception as e:
            logger.warning("Gemini generation failed: %s, falling back to heuristic", e)

        # Fallback to heuristic client on API error
        return HeuristicGoldenSqlClient().generate_candidates(ctx, n=n)

    def repair_sql(self, ctx: SqlPromptContext, broken_sql: str, sanitized_error: str) -> str:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = ChatGoogleGenerativeAI(
                model=self.settings.llm_model,
                google_api_key=self.settings.google_api_key,
                temperature=0.0,
            )

            prompt = (
                "Bạn là chuyên gia sửa lỗi SQL PostgreSQL cho schema ai_views.\n"
                f"Schema danh mục:\n{ctx.catalog_markdown}\n\n"
                f"SQL bị lỗi:\n```sql\n{broken_sql}\n```\n"
                f"Thông báo lỗi đã làm sạch:\n{sanitized_error}\n\n"
                "Hãy sửa lỗi và chỉ trả về duy nhất câu lệnh SQL đã sửa chữa trong khối ```sql ... ```."
            )

            res = llm.invoke([HumanMessage(content=prompt)])
            text = str(res.content)
            match = re.search(r"```(?:sql)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
            return text.strip()
        except Exception as e:
            logger.warning("Gemini repair failed: %s", e)
            return HeuristicGoldenSqlClient().repair_sql(ctx, broken_sql, sanitized_error)

    def _parse_json_candidates(self, text: str) -> list[SqlDraft]:
        try:
            # Match json block
            match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return [SqlDraft(**item) for item in data if "sql" in item]
            # Try single object
            match_obj = re.search(r"\{\s*\"sql\".*\}", text, re.DOTALL)
            if match_obj:
                data = json.loads(match_obj.group(0))
                return [SqlDraft(**data)]
        except Exception:
            pass
        return []


class OllamaSqlLLMClient:
    """Local Ollama SQL generator endpoint client."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate_candidates(self, ctx: SqlPromptContext, n: int = 3) -> list[SqlDraft]:
        if ctx.known_missing_data_reason:
            return [
                SqlDraft(
                    sql="",
                    explanation_short=ctx.known_missing_data_reason,
                    out_of_scope_reason=ctx.known_missing_data_reason,
                )
            ]

        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        model = self.settings.llm_model or "qwen2.5-coder:7b"
        prompt = (
            f"Tạo câu SQL PostgreSQL schema ai_views cho câu hỏi: {ctx.question}\n"
            f"Views:\n{ctx.catalog_markdown}\n"
            "Chỉ trả về JSON format: [{\"sql\": \"...\", \"explanation_short\": \"...\"}]"
        )
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                response_text = data.get("response", "")
                match = re.search(r"\[\s*\{.*\}\s*\]", response_text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    return [SqlDraft(**item) for item in parsed if "sql" in item]
        except Exception as e:
            logger.warning("Ollama generation failed (%s), falling back to heuristic", e)

        return HeuristicGoldenSqlClient().generate_candidates(ctx, n=n)

    def repair_sql(self, ctx: SqlPromptContext, broken_sql: str, sanitized_error: str) -> str:
        model = self.settings.llm_model or "qwen2.5-coder:7b"
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        prompt = (
            "Bạn là chuyên gia sửa lỗi SQL PostgreSQL cho schema ai_views.\n"
            f"Schema danh mục:\n{ctx.catalog_markdown}\n\n"
            f"SQL bị lỗi:\n```sql\n{broken_sql}\n```\n"
            f"Thông báo lỗi đã làm sạch:\n{sanitized_error}\n\n"
            "Hãy sửa lỗi và chỉ trả về duy nhất câu lệnh SQL đã sửa chữa trong khối ```sql ... ```."
        )
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                response_text = data.get("response", "")
                match = re.search(r"```(?:sql)?(.*?)```", response_text, re.DOTALL | re.IGNORECASE)
                if match:
                    return match.group(1).strip()
                if response_text.strip():
                    return response_text.strip()
        except Exception as e:
            logger.warning("Ollama repair failed (%s), falling back to heuristic", e)

        return HeuristicGoldenSqlClient().repair_sql(ctx, broken_sql, sanitized_error)


def create_sql_llm_client(
    provider: str = "auto",
    settings: Settings | None = None,
) -> tuple[SqlLLMClient, str]:
    """Factory to instantiate the appropriate SQL LLM client.

    Returns:
        tuple[SqlLLMClient, str]: The instantiated client and effective provider identifier.
    """
    cfg = settings or get_settings()
    prov = (provider or "auto").strip().lower()

    if prov == "mock":
        return MockSqlLLMClient(), "mock"

    if prov == "heuristic":
        return HeuristicGoldenSqlClient(), "heuristic"

    if prov == "gemini":
        return GeminiSqlLLMClient(settings=cfg), "gemini"

    if prov == "ollama":
        return OllamaSqlLLMClient(settings=cfg), "ollama"

    if prov == "auto":
        # Check if Gemini API key is configured with a real key
        key = cfg.google_api_key or ""
        if key and not key.startswith("mock_") and not key.startswith("your_") and len(key) > 20:
            return GeminiSqlLLMClient(settings=cfg), "gemini"

        # Check if local Ollama server is responding
        try:
            req = urllib.request.Request(f"{cfg.ollama_base_url.rstrip('/')}/api/tags")
            with urllib.request.urlopen(req, timeout=1):
                return OllamaSqlLLMClient(settings=cfg), "ollama"
        except Exception:
            pass

        # Default fallback to deterministic heuristic client
        return HeuristicGoldenSqlClient(), "heuristic"

    return HeuristicGoldenSqlClient(), "heuristic"
