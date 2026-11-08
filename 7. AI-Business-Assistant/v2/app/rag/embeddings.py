"""Embedding providers for T2-RAG layer.

Provides deterministic local hashing embeddings (offline, fast, reproducible)
as well as cloud/local LLM embedding options.
"""

from typing import Protocol, runtime_checkable
import requests

from sklearn.feature_extraction.text import HashingVectorizer

from app.core.config import Settings, get_settings
from app.knowledge.loader import prepare_search_text


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol defining the embedding interface."""

    signature: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class DeterministicLocalEmbeddingProvider:
    """Deterministic, stateless n-gram hashing embedding provider.

    Uses character word-boundary n-grams over normalized accented & unaccented text
    to guarantee vocabulary consistency across independent incremental re-indexing runs.
    """

    def __init__(self, n_features: int = 512):
        self.n_features = n_features
        self.signature = f"deterministic-hash-{n_features}"
        self._vectorizer = HashingVectorizer(
            n_features=n_features,
            norm="l2",
            alternate_sign=False,
            analyzer="char_wb",
            ngram_range=(3, 5),
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        prepared = [prepare_search_text(t) for t in texts]
        arr = self._vectorizer.transform(prepared).toarray()
        return arr.tolist()

    def embed_query(self, text: str) -> list[float]:
        prepared = prepare_search_text(text)
        arr = self._vectorizer.transform([prepared]).toarray()
        return arr[0].tolist()


class OllamaEmbeddingProvider:
    """Local embedding provider using self-hosted Ollama."""

    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.signature = f"ollama-{model}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=10,
            )
            resp.raise_for_status()
            results.append(resp.json()["embedding"])
        return results

    def embed_query(self, text: str) -> list[float]:
        docs = self.embed_documents([text])
        return docs[0] if docs else []


class GeminiEmbeddingProvider:
    """Cloud embedding provider using Google Gemini Embeddings."""

    def __init__(self, model: str = "text-embedding-004", api_key: str = ""):
        self.model = model
        self.api_key = api_key
        self.signature = f"gemini-{model}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Fallback or external call
        raise NotImplementedError("GeminiEmbeddingProvider requires active API key.")

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def create_embedding_provider(
    provider: str = "auto",
    settings: Settings | None = None,
) -> tuple[EmbeddingProvider, str]:
    """Factory creating an EmbeddingProvider based on provider preference and config."""
    cfg = settings or get_settings()
    target = provider.strip().lower() if provider != "auto" else cfg.embedding_provider.strip().lower()

    if target in ("deterministic", "hash", "local"):
        return DeterministicLocalEmbeddingProvider(), "deterministic"

    if target == "ollama":
        try:
            p = OllamaEmbeddingProvider(model=cfg.embedding_model, base_url=cfg.ollama_base_url)
            # Ping ollama
            requests.get(f"{cfg.ollama_base_url}/api/tags", timeout=1.0)
            return p, "ollama"
        except Exception:
            return DeterministicLocalEmbeddingProvider(), "deterministic"

    if target == "gemini" and cfg.google_api_key:
        return GeminiEmbeddingProvider(model=cfg.embedding_model, api_key=cfg.google_api_key), "gemini"

    # Default auto falls back to deterministic local
    return DeterministicLocalEmbeddingProvider(), "deterministic"
