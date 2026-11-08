"""Hybrid RAG retriever combining ChromaDB Vector Search + BM25Okapi + Reciprocal Rank Fusion (RRF).

Specifications:
- Spec Phần II §5 (Semantic Knowledge Layer)
- Review Focus #4: RBAC document-level access filtering
- TC-T2-06: Vietnamese unaccented retrieval with RRF rank fusion
"""

from pathlib import Path
from typing import Any

import chromadb
from rank_bm25 import BM25Okapi

from app.core.config import Settings, get_settings
from app.knowledge.loader import prepare_search_text
from app.rag.embeddings import EmbeddingProvider, create_embedding_provider
from app.rag.models import RetrievedChunk

_RETRIEVER_DIR = Path(__file__).resolve().parent
V2_ROOT = _RETRIEVER_DIR.parents[1]


class HybridRagRetriever:
    """Hybrid semantic retriever using ChromaDB vector search and BM25Okapi with RRF."""

    def __init__(
        self,
        persist_dir: Path | None = None,
        manifest_path: Path | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        collection_name: str = "gml_business_docs",
        rrf_k: int = 60,
    ):
        settings = get_settings()

        p_dir = persist_dir or Path(settings.chroma_persist_dir)
        self.persist_dir = p_dir if p_dir.is_absolute() else (V2_ROOT / p_dir)

        m_path = manifest_path or Path(settings.rag_manifest_path)
        self.manifest_path = m_path if m_path.is_absolute() else (V2_ROOT / m_path)

        self.collection_name = collection_name
        self.rrf_k = rrf_k

        if embedding_provider is None:
            self.embedding_provider, _ = create_embedding_provider(settings=settings)
        else:
            self.embedding_provider = embedding_provider

        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def retrieve(
        self,
        query: str,
        role: str = "ceo",
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> list[RetrievedChunk]:
        """Retrieve top_k chunks using hybrid Vector + BM25 search with RBAC filtering and RRF ranking."""
        role_filter = {f"role_{role}": True}

        # Step 1: Pre-filter by RBAC role. If no documents allowed, return empty list immediately.
        try:
            allowed = self.collection.get(
                where=role_filter,
                include=["documents", "metadatas"],
            )
        except Exception:
            return []

        allowed_ids: list[str] = allowed.get("ids", [])
        if not allowed_ids:
            return []

        allowed_docs: list[str] = allowed.get("documents", [])
        allowed_metas: list[dict[str, Any]] = allowed.get("metadatas", [])
        total_allowed = len(allowed_ids)

        # Step 2: Keyword ranking via BM25Okapi over allowed documents
        bm25_rank_map: dict[str, int] = {}
        try:
            tokenized_corpus = [prepare_search_text(doc).split() for doc in allowed_docs]
            bm25 = BM25Okapi(tokenized_corpus)
            query_tokens = prepare_search_text(query).split()
            if query_tokens:
                bm25_scores = bm25.get_scores(query_tokens)
                pos_indices = [i for i in range(total_allowed) if bm25_scores[i] > 0]
                if pos_indices:
                    sorted_pos = sorted(pos_indices, key=lambda i: bm25_scores[i], reverse=True)
                    for rank, idx in enumerate(sorted_pos[:candidate_k], start=1):
                        bm25_rank_map[allowed_ids[idx]] = rank
        except Exception:
            bm25_rank_map = {}

        # Step 3: Vector ranking via ChromaDB cosine similarity over allowed documents
        vector_rank_map: dict[str, int] = {}
        try:
            query_embedding = self.embedding_provider.embed_query(query)
            n_query = min(candidate_k, total_allowed)
            v_res = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_query,
                where=role_filter,
            )
            if v_res and v_res.get("ids") and v_res["ids"][0]:
                for rank, chunk_id in enumerate(v_res["ids"][0], start=1):
                    vector_rank_map[chunk_id] = rank
        except Exception:
            vector_rank_map = {}

        # Step 4: Reciprocal Rank Fusion (RRF)
        # score(d) = 1 / (rrf_k + rank_vec(d)) + 1 / (rrf_k + rank_bm25(d))
        candidate_ids = set(bm25_rank_map.keys()) | set(vector_rank_map.keys())
        if not candidate_ids:
            candidate_ids = set(allowed_ids[:top_k])

        meta_by_id = {
            allowed_ids[i]: (allowed_docs[i], allowed_metas[i])
            for i in range(total_allowed)
        }

        scored_candidates: list[tuple[float, int | None, int | None, str]] = []
        for chunk_id in candidate_ids:
            if chunk_id not in meta_by_id:
                continue
            v_rank = vector_rank_map.get(chunk_id)
            b_rank = bm25_rank_map.get(chunk_id)
            score = 0.0
            if v_rank is not None:
                score += 1.0 / (self.rrf_k + v_rank)
            if b_rank is not None:
                score += 1.0 / (self.rrf_k + b_rank)
            scored_candidates.append((score, v_rank, b_rank, chunk_id))

        # Sort descending by RRF score, secondary by chunk_id
        scored_candidates.sort(key=lambda item: (-item[0], item[3]))

        results: list[RetrievedChunk] = []
        for score, v_rank, b_rank, chunk_id in scored_candidates[:top_k]:
            doc_text, meta = meta_by_id[chunk_id]
            content = meta.get("content", doc_text)
            results.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    source=meta.get("source", ""),
                    heading_path=meta.get("heading_path", ""),
                    content=content,
                    dashboard=meta.get("dashboard", ""),
                    doc_type=meta.get("doc_type", ""),
                    score=score,
                    vector_rank=v_rank,
                    bm25_rank=b_rank,
                )
            )

        return results
