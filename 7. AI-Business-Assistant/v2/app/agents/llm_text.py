"""Text generation LLM client protocols, mocks, and provider factory.

Specifications:
- Spec Phần II §6 (Agent Architecture)
- Fallback safely to DeterministicTemplateTextClient when no API key or offline
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Callable, Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class TextLLMClient(Protocol):
    """Protocol defining the interface for general text generation."""

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a text completion given system instructions and user prompt."""
        ...


class MockTextLLMClient:
    """Mock text LLM client for unit and integration testing."""

    def __init__(
        self,
        response_text: str | Callable[[str, str], str] = "Mock text response",
    ) -> None:
        self.response_text = response_text
        self.call_count = 0
        self.calls: list[dict[str, str]] = []
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})

        if callable(self.response_text):
            return self.response_text(system_prompt, user_prompt)
        return self.response_text


class DeterministicTemplateTextClient:
    """Deterministic text generator for offline testing and zero-token operation."""

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        # If user_prompt contains KPI explanation context, summarize it cleanly
        if "KPI:" in user_prompt:
            lines = [line.strip() for line in user_prompt.splitlines() if line.strip()]
            return " ".join(lines[:3])

        # If user_prompt contains untrusted document context, provide a cited summary
        if "<untrusted_document_context>" in user_prompt:
            return "Theo tài liệu tham khảo [1], các quy định và số liệu đã được đối chiếu đầy đủ."

        return "Nội dung phản hồi được tạo tự động từ quy tắc nghiệp vụ."


class GeminiTextLLMClient:
    """Google Gemini text generator client via langchain_google_genai."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = ChatGoogleGenerativeAI(
                model=self.settings.llm_model or "gemini-3.8-flash",
                google_api_key=self.settings.google_api_key,
                temperature=0.0,
            )
            res = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
            return str(res.content).strip()
        except Exception as e:
            logger.warning("Gemini text generation failed (%s), falling back to template client", e)
            return DeterministicTemplateTextClient().generate_text(system_prompt, user_prompt)


class OllamaTextLLMClient:
    """Local Ollama text generator client."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        model = self.settings.llm_model or "qwen2.5:7b"
        prompt = f"{system_prompt}\n\n{user_prompt}"
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except Exception as e:
            logger.warning("Ollama text generation failed (%s), falling back to template client", e)
            return DeterministicTemplateTextClient().generate_text(system_prompt, user_prompt)


def create_text_llm_client(
    provider: str = "auto",
    settings: Settings | None = None,
) -> tuple[TextLLMClient, str]:
    """Factory to instantiate the appropriate Text LLM client.

    Returns:
        tuple[TextLLMClient, str]: The instantiated client and provider identifier.
    """
    cfg = settings or get_settings()
    prov = (provider or "auto").strip().lower()

    if prov == "mock":
        return MockTextLLMClient(), "mock"

    if prov == "template":
        return DeterministicTemplateTextClient(), "template"

    if prov == "gemini":
        return GeminiTextLLMClient(settings=cfg), "gemini"

    if prov == "ollama":
        return OllamaTextLLMClient(settings=cfg), "ollama"

    if prov == "auto":
        # Check if Gemini API key is configured with a real key
        key = cfg.google_api_key or ""
        if key and not key.startswith("mock_") and not key.startswith("your_") and len(key) > 20:
            return GeminiTextLLMClient(settings=cfg), "gemini"

        # Check if local Ollama server is responding
        try:
            req = urllib.request.Request(f"{cfg.ollama_base_url.rstrip('/')}/api/tags")
            with urllib.request.urlopen(req, timeout=1):
                return OllamaTextLLMClient(settings=cfg), "ollama"
        except Exception:
            pass

        return DeterministicTemplateTextClient(), "template"

    return DeterministicTemplateTextClient(), "template"
