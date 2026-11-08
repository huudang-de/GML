"""T2-RAG semantic retrieval layer package.

Exposes models, embedding providers, ingestion pipeline, and hybrid retriever.
"""

from app.rag.embeddings import (
    DeterministicLocalEmbeddingProvider,
    EmbeddingProvider,
    GeminiEmbeddingProvider,
    OllamaEmbeddingProvider,
    create_embedding_provider,
)
from app.rag.ingest import (
    CORPUS_REGISTRY,
    chunk_markdown_by_headings,
    ingest_corpus,
)
from app.rag.models import (
    DocumentChunk,
    IngestReport,
    RagDocumentSpec,
    RetrievedChunk,
)
from app.rag.retriever import HybridRagRetriever

__all__ = [
    "RagDocumentSpec",
    "DocumentChunk",
    "IngestReport",
    "RetrievedChunk",
    "EmbeddingProvider",
    "DeterministicLocalEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "create_embedding_provider",
    "CORPUS_REGISTRY",
    "chunk_markdown_by_headings",
    "ingest_corpus",
    "HybridRagRetriever",
]
