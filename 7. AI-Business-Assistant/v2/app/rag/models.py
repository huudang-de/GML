"""Data models for T2-RAG semantic retrieval layer.

Specifications:
- Spec Phần II §5 (Semantic Knowledge Layer)
- Review Focus #4: RBAC document filtering
- Review Focus #5: Idempotency & Clean Reindex
"""

from typing import Literal
from pydantic import BaseModel, Field


class RagDocumentSpec(BaseModel):
    """Specification of a document in the RAG corpus."""

    source: str
    rel_path: str
    dashboard: str
    doc_type: Literal["dashboard_guide", "handbook", "storytelling", "financial_knowledge"]
    allowed_roles: list[str]


class DocumentChunk(BaseModel):
    """A granular chunk of markdown document aware of its heading breadcrumbs."""

    chunk_id: str
    source: str
    heading_path: str
    content: str
    dashboard: str
    doc_type: str
    allowed_roles: list[str]
    doc_sha256: str
    chunk_index: int


class IngestReport(BaseModel):
    """Report detailing the results of an ingestion run."""

    total_files: int
    added_files: list[str] = Field(default_factory=list)
    updated_files: list[str] = Field(default_factory=list)
    unchanged_files: list[str] = Field(default_factory=list)
    removed_files: list[str] = Field(default_factory=list)
    indexed_chunks: int = 0
    deleted_chunks: int = 0
    embedding_signature: str = ""


class RetrievedChunk(BaseModel):
    """A retrieved chunk enriched with hybrid ranking information."""

    chunk_id: str
    source: str
    heading_path: str
    content: str
    dashboard: str
    doc_type: str
    score: float
    vector_rank: int | None = None
    bm25_rank: int | None = None
