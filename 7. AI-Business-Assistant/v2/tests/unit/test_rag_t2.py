"""Unit tests for T2-RAG layer: versioned SHA-256 ingestion, chunking, and hybrid retrieval.

Specifications:
- TC-T2-04: Ingestion idempotency (re-indexing unchanged files indexes 0 chunks)
- TC-T2-05: Ingestion detects single file change and cleans orphaned chunks without leak
- Embedding signature change triggers complete re-index
- TC-T2-06: Unaccented Vietnamese hybrid retrieval in top-5
- RBAC filtering blocks sensitive documents for warehouse manager and sysadmin
"""

from pathlib import Path
import unicodedata
import pytest

from app.rag.embeddings import DeterministicLocalEmbeddingProvider
from app.rag.ingest import CORPUS_REGISTRY, chunk_markdown_by_headings, ingest_corpus
from app.rag.models import RagDocumentSpec
from app.rag.retriever import HybridRagRetriever


def test_tc_t2_04_ingest_idempotent(tmp_path: Path):
    """TC-T2-04: Unchanged files index 0 chunks on subsequent runs."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    d1 = docs_dir / "guide_dashboard1.md"
    d1.write_text(
        "# Dashboard 1\n\nNội dung quản trị tài chính doanh nghiệp.\n\n## Mục 1.1\n\nChi tiết tài chính.",
        encoding="utf-8",
    )
    d2 = docs_dir / "guide_dashboard2.md"
    d2.write_text(
        "# Dashboard 2\n\nNội dung quản trị tồn kho hàng hóa.\n\n## Mục 2.1\n\nTồn kho an toàn.",
        encoding="utf-8",
    )

    specs = [
        RagDocumentSpec(
            source="guide_dashboard1.md",
            rel_path="guide_dashboard1.md",
            dashboard="D1",
            doc_type="dashboard_guide",
            allowed_roles=["ceo", "ke_toan_truong"],
        ),
        RagDocumentSpec(
            source="guide_dashboard2.md",
            rel_path="guide_dashboard2.md",
            dashboard="D2",
            doc_type="dashboard_guide",
            allowed_roles=["ceo", "ke_toan_truong", "quan_ly_kho"],
        ),
    ]
    docs = [(specs[0], d1), (specs[1], d2)]

    persist_dir = tmp_path / "chroma"
    manifest_path = tmp_path / "manifest.json"
    provider = DeterministicLocalEmbeddingProvider(n_features=256)

    # First ingest
    report1 = ingest_corpus(
        docs=docs,
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=provider,
    )
    assert report1.indexed_chunks > 0
    assert set(report1.added_files) == {"guide_dashboard1.md", "guide_dashboard2.md"}
    assert report1.total_files == 2

    # Second ingest without file modifications
    report2 = ingest_corpus(
        docs=docs,
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=provider,
    )
    assert report2.indexed_chunks == 0
    assert report2.added_files == []
    assert report2.updated_files == []
    assert len(report2.unchanged_files) == 2
    assert set(report2.unchanged_files) == {"guide_dashboard1.md", "guide_dashboard2.md"}


def test_tc_t2_05_ingest_detects_single_file_change_and_cleans_orphans(tmp_path: Path):
    """TC-T2-05: Modifying a file reindexes only that file and purges deleted chunks from ChromaDB."""
    import chromadb

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    d1 = docs_dir / "guide_dashboard1.md"
    d1.write_text("# Dashboard 1\n\nNội dung quản trị tài chính.", encoding="utf-8")
    d3 = docs_dir / "guide_dashboard3.md"
    d3.write_text(
        "# Dashboard 3: Quản trị Phải Thu - Phải Trả\n\nNội dung tổng quan.\n\n"
        "## Phải Thu Khách Hàng\n\nChi tiết công nợ phải thu.\n\n"
        "### Mục Cần Xóa\n\nNội dung tạm thời cần xoá sau này.",
        encoding="utf-8",
    )

    specs = [
        RagDocumentSpec(
            source="guide_dashboard1.md",
            rel_path="guide_dashboard1.md",
            dashboard="D1",
            doc_type="dashboard_guide",
            allowed_roles=["ceo", "ke_toan_truong"],
        ),
        RagDocumentSpec(
            source="guide_dashboard3.md",
            rel_path="guide_dashboard3.md",
            dashboard="D3",
            doc_type="dashboard_guide",
            allowed_roles=["ceo", "ke_toan_truong"],
        ),
    ]
    docs = [(specs[0], d1), (specs[1], d3)]

    persist_dir = tmp_path / "chroma"
    manifest_path = tmp_path / "manifest.json"
    provider = DeterministicLocalEmbeddingProvider(n_features=256)

    # Initial ingest
    report1 = ingest_corpus(
        docs=docs,
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=provider,
    )
    assert report1.indexed_chunks > 0

    # Verify that the chunk to be deleted exists in ChromaDB
    client = chromadb.PersistentClient(path=str(persist_dir))
    coll = client.get_collection("gml_business_docs")
    before_chunks = coll.get()
    deleted_heading_found = any("Mục Cần Xóa" in doc for doc in before_chunks["documents"])
    assert deleted_heading_found, "Before re-index, 'Mục Cần Xóa' chunk should exist"

    # Modify guide_dashboard3.md: remove '### Mục Cần Xóa'
    d3.write_text(
        "# Dashboard 3: Quản trị Phải Thu - Phải Trả\n\nNội dung tổng quan đã cập nhật.\n\n"
        "## Phải Thu Khách Hàng\n\nChi tiết công nợ phải thu cập nhật.",
        encoding="utf-8",
    )

    # Re-run ingest
    report2 = ingest_corpus(
        docs=docs,
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=provider,
    )
    assert report2.updated_files == ["guide_dashboard3.md"]
    assert report2.unchanged_files == ["guide_dashboard1.md"]
    assert report2.added_files == []

    # Verify orphan cleanup: the deleted section must no longer exist in ChromaDB
    after_chunks = coll.get()
    after_heading_found = any("Mục Cần Xóa" in doc for doc in after_chunks["documents"])
    assert not after_heading_found, "Orphan chunk 'Mục Cần Xóa' must be removed from ChromaDB"


def test_embedding_signature_change_triggers_full_reindex(tmp_path: Path):
    """Review Focus #5: Changing embedding signature drops old collection and re-indexes all files."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    d1 = docs_dir / "guide_dashboard1.md"
    d1.write_text("# Dashboard 1\n\nNội dung quản trị tài chính.", encoding="utf-8")
    d2 = docs_dir / "guide_dashboard2.md"
    d2.write_text("# Dashboard 2\n\nNội dung quản trị tồn kho.", encoding="utf-8")

    specs = [
        RagDocumentSpec(
            source="guide_dashboard1.md",
            rel_path="guide_dashboard1.md",
            dashboard="D1",
            doc_type="dashboard_guide",
            allowed_roles=["ceo", "ke_toan_truong"],
        ),
        RagDocumentSpec(
            source="guide_dashboard2.md",
            rel_path="guide_dashboard2.md",
            dashboard="D2",
            doc_type="dashboard_guide",
            allowed_roles=["ceo", "ke_toan_truong", "quan_ly_kho"],
        ),
    ]
    docs = [(specs[0], d1), (specs[1], d2)]

    persist_dir = tmp_path / "chroma"
    manifest_path = tmp_path / "manifest.json"

    # Ingest 1 with 256 features
    p256 = DeterministicLocalEmbeddingProvider(n_features=256)
    report1 = ingest_corpus(
        docs=docs,
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=p256,
    )
    assert report1.embedding_signature == "deterministic-hash-256"
    assert len(report1.added_files) == 2

    # Ingest 2 with 512 features (signature changed)
    p512 = DeterministicLocalEmbeddingProvider(n_features=512)
    report2 = ingest_corpus(
        docs=docs,
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=p512,
    )
    assert report2.embedding_signature == "deterministic-hash-512"
    # Should reindex all 2 files (none unchanged)
    assert len(report2.unchanged_files) == 0
    assert len(report2.updated_files) + len(report2.added_files) == 2


def test_tc_t2_06_unaccented_vietnamese_retrieval_top5(tmp_path: Path):
    """TC-T2-06: Retrieval with unaccented query returns definition of 'vòng quay phải thu' in top-5."""
    persist_dir = tmp_path / "chroma"
    manifest_path = tmp_path / "manifest.json"
    provider = DeterministicLocalEmbeddingProvider(n_features=512)

    # Ingest the 8 real project documents
    report = ingest_corpus(
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=provider,
    )
    assert report.total_files == 8

    retriever = HybridRagRetriever(
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=provider,
    )
    chunks = retriever.retrieve("vong quay phai thu", role="ke_toan_truong", top_k=5)
    assert len(chunks) == 5

    # Check NFC normalized definition of "vòng quay phải thu" in at least one chunk in top 5
    found = False
    for c in chunks:
        content_nfc = unicodedata.normalize("NFC", c.content).lower()
        if "vòng quay phải thu" in content_nfc:
            found = True
            break
    assert found, "Top 5 retrieved chunks must contain definition of 'vòng quay phải thu'"


def test_rag_rbac_blocks_sensitive_docs_for_warehouse_and_admin(tmp_path: Path):
    """Review Focus #4: RBAC blocks restricted documents for warehouse manager and sysadmin."""
    persist_dir = tmp_path / "chroma"
    manifest_path = tmp_path / "manifest.json"
    provider = DeterministicLocalEmbeddingProvider(n_features=512)

    ingest_corpus(
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=provider,
    )
    retriever = HybridRagRetriever(
        persist_dir=persist_dir,
        manifest_path=manifest_path,
        embedding_provider=provider,
    )

    # Warehouse manager query for sensitive finance data
    wh_chunks = retriever.retrieve(
        "tỷ lệ sử dụng hạn mức vay ngân hàng 236,07 tỷ",
        role="quan_ly_kho",
        top_k=5,
    )
    forbidden_sources = {
        "Story Telling báo cáo quản trị tài chính – Gỗ Minh Long.md",
        "guide_dashboard1.md",
        "guide_dashboard3.md",
        "guide_dashboard4.md",
        "guide_dashboard5.md",
    }
    for chunk in wh_chunks:
        assert chunk.source not in forbidden_sources, (
            f"Role quan_ly_kho received forbidden document: {chunk.source}"
        )

    # System admin query -> absolute empty list (0 allowed documents)
    admin_chunks = retriever.retrieve("bất kỳ câu hỏi nào", role="quan_tri_he_thong", top_k=5)
    assert admin_chunks == [], "Role quan_tri_he_thong has 0 allowed documents and must receive []"
