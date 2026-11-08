"""Markdown chunking, SHA-256 versioning, and ChromaDB ingestion pipeline.

Specifications:
- TC-T2-04: Idempotency (unchanged files index 0 chunks)
- TC-T2-05: Clean orphan purge on file update
- Review Focus #4: RBAC document-level access permissions
- Review Focus #5: Embedding signature change triggers complete re-index
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import unicodedata

import chromadb

from app.core.config import Settings, get_settings
from app.rag.embeddings import (
    DeterministicLocalEmbeddingProvider,
    EmbeddingProvider,
    create_embedding_provider,
)
from app.rag.models import DocumentChunk, IngestReport, RagDocumentSpec

# Paths relative to this file
_RAG_DIR = Path(__file__).resolve().parent
V2_ROOT = _RAG_DIR.parents[1]  # 7. AI-Business-Assistant/v2
WORKSPACE_ROOT = _RAG_DIR.parents[3]  # Workspace root directory

# Registry of 8 core project documents with RBAC constraints
CORPUS_REGISTRY: list[RagDocumentSpec] = [
    RagDocumentSpec(
        source="guide_dashboard1.md",
        rel_path="4. Phát triển báo cáo/guide_dashboard1.md",
        dashboard="D1",
        doc_type="dashboard_guide",
        allowed_roles=["ceo", "ke_toan_truong"],
    ),
    RagDocumentSpec(
        source="guide_dashboard2.md",
        rel_path="4. Phát triển báo cáo/guide_dashboard2.md",
        dashboard="D2",
        doc_type="dashboard_guide",
        allowed_roles=["ceo", "ke_toan_truong", "quan_ly_kho"],
    ),
    RagDocumentSpec(
        source="guide_dashboard3.md",
        rel_path="4. Phát triển báo cáo/guide_dashboard3.md",
        dashboard="D3",
        doc_type="dashboard_guide",
        allowed_roles=["ceo", "ke_toan_truong"],
    ),
    RagDocumentSpec(
        source="guide_dashboard4.md",
        rel_path="4. Phát triển báo cáo/guide_dashboard4.md",
        dashboard="D4",
        doc_type="dashboard_guide",
        allowed_roles=["ceo", "ke_toan_truong"],
    ),
    RagDocumentSpec(
        source="guide_dashboard5.md",
        rel_path="4. Phát triển báo cáo/guide_dashboard5.md",
        dashboard="D5",
        doc_type="dashboard_guide",
        allowed_roles=["ceo", "ke_toan_truong"],
    ),
    RagDocumentSpec(
        source="Cam_nang_Nghiep_vu_Toan_thu_GML.md",
        rel_path="2. Tài liệu phân tích và thiết kế/01. Tài liệu tổng thể/Cam_nang_Nghiep_vu_Toan_thu_GML.md",
        dashboard="ALL",
        doc_type="handbook",
        allowed_roles=["ceo", "ke_toan_truong", "quan_ly_kho"],
    ),
    RagDocumentSpec(
        source="Story Telling báo cáo quản trị tài chính – Gỗ Minh Long.md",
        rel_path="4. Phát triển báo cáo/Story Telling báo cáo quản trị tài chính – Gỗ Minh Long.md",
        dashboard="ALL",
        doc_type="storytelling",
        allowed_roles=["ceo", "ke_toan_truong"],
    ),
    RagDocumentSpec(
        source="Tai_lieu_Tri_thuc_Quan_tri_Tai_chinh_GML.md",
        rel_path="7. AI-Business-Assistant/Tài liệu tham khảo/File_tri_thuc/Tai_lieu_Tri_thuc_Quan_tri_Tai_chinh_GML.md",
        dashboard="ALL",
        doc_type="financial_knowledge",
        allowed_roles=["ceo", "ke_toan_truong", "quan_ly_kho"],
    ),
]


def _split_section_text(text: str, max_chars: int = 1200, overlap_chars: int = 150) -> list[str]:
    """Split section content into chunks under max_chars by paragraphs with overlap."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        step = max(1, max_chars - overlap_chars)
        return [text[i : i + max_chars].strip() for i in range(0, len(text), step)]

    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if len(p) > max_chars:
            step = max(1, max_chars - overlap_chars)
            for i in range(0, len(p), step):
                sub = p[i : i + max_chars].strip()
                if current:
                    chunks.append(current)
                    current = ""
                if sub:
                    chunks.append(sub)
            continue

        candidate = f"{current}\n\n{p}".strip() if current else p
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
                tail = current[-overlap_chars:].strip() if len(current) > overlap_chars else current
                current = f"{tail}\n\n{p}".strip()
                if len(current) > max_chars:
                    current = p
            else:
                current = p

    if current and current.strip():
        chunks.append(current.strip())

    return chunks


def chunk_markdown_by_headings(
    markdown_text: str,
    doc_spec: RagDocumentSpec,
    doc_sha256: str,
    max_chars: int = 1200,
    overlap_chars: int = 150,
) -> list[DocumentChunk]:
    """Normalize text into NFC, split by headings (# to ####) tracking breadcrumbs, and chunk long sections."""
    nfc_text = unicodedata.normalize("NFC", markdown_text or "")
    lines = nfc_text.splitlines()

    stack: list[tuple[int, str]] = []  # (level, title)
    sections: list[tuple[str, str]] = []  # (heading_path, content)
    current_lines: list[str] = []

    heading_re = re.compile(r"^(#{1,4})\s+(.+)$")

    for line in lines:
        m = heading_re.match(line)
        if m:
            if current_lines and "\n".join(current_lines).strip():
                hp = " > ".join(t for _, t in stack) if stack else "Overview"
                sections.append((hp, "\n".join(current_lines).strip()))
                current_lines = []

            level = len(m.group(1))
            title = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        else:
            current_lines.append(line)

    if current_lines and "\n".join(current_lines).strip():
        hp = " > ".join(t for _, t in stack) if stack else "Overview"
        sections.append((hp, "\n".join(current_lines).strip()))

    chunks: list[DocumentChunk] = []
    chunk_index = 0

    for hp, content in sections:
        pieces = _split_section_text(content, max_chars=max_chars, overlap_chars=overlap_chars)
        for piece in pieces:
            chunk = DocumentChunk(
                chunk_id=f"{doc_spec.source}#c{chunk_index:04d}",
                source=doc_spec.source,
                heading_path=hp,
                content=piece,
                dashboard=doc_spec.dashboard,
                doc_type=doc_spec.doc_type,
                allowed_roles=doc_spec.allowed_roles,
                doc_sha256=doc_sha256,
                chunk_index=chunk_index,
            )
            chunks.append(chunk)
            chunk_index += 1

    return chunks


def ingest_corpus(
    docs: list[tuple[RagDocumentSpec, Path]] | None = None,
    persist_dir: Path | None = None,
    manifest_path: Path | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    collection_name: str = "gml_business_docs",
    max_chars: int = 1200,
) -> IngestReport:
    """Ingest documents into ChromaDB with SHA-256 versioning, idempotency, and orphan cleanup."""
    settings = get_settings()

    p_dir = persist_dir or Path(settings.chroma_persist_dir)
    target_persist = p_dir if p_dir.is_absolute() else (V2_ROOT / p_dir)
    target_persist.mkdir(parents=True, exist_ok=True)

    m_path = manifest_path or Path(settings.rag_manifest_path)
    target_manifest = m_path if m_path.is_absolute() else (V2_ROOT / m_path)
    target_manifest.parent.mkdir(parents=True, exist_ok=True)

    if embedding_provider is None:
        provider, _ = create_embedding_provider(settings=settings)
    else:
        provider = embedding_provider

    if docs is None:
        docs = [(spec, WORKSPACE_ROOT / spec.rel_path) for spec in CORPUS_REGISTRY]

    # Load or initialize manifest
    if target_manifest.exists():
        try:
            manifest_data: dict[str, Any] = json.loads(target_manifest.read_text(encoding="utf-8"))
        except Exception:
            manifest_data = {"embedding_signature": "", "files": {}}
    else:
        manifest_data = {"embedding_signature": "", "files": {}}

    client = chromadb.PersistentClient(path=str(target_persist))

    # Detect embedding signature change -> force full re-index
    current_sig = provider.signature
    stored_sig = manifest_data.get("embedding_signature", "")
    if stored_sig and stored_sig != current_sig:
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass
        manifest_data["files"] = {}

    manifest_data["embedding_signature"] = current_sig
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    total_files = len(docs)
    added_files: list[str] = []
    updated_files: list[str] = []
    unchanged_files: list[str] = []
    removed_files: list[str] = []
    indexed_chunks = 0
    deleted_chunks = 0

    current_source_names = {spec.source for spec, _ in docs}

    # Clean up removed files
    for old_source, old_info in list(manifest_data.get("files", {}).items()):
        if old_source not in current_source_names:
            old_ids = old_info.get("chunk_ids", [])
            if old_ids:
                try:
                    collection.delete(ids=old_ids)
                except Exception:
                    pass
                deleted_chunks += len(old_ids)
            del manifest_data["files"][old_source]
            removed_files.append(old_source)

    # Process each document
    for doc_spec, doc_path in docs:
        raw_bytes = doc_path.read_bytes()
        file_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        prev_entry = manifest_data.get("files", {}).get(doc_spec.source)
        if prev_entry and prev_entry.get("sha256") == file_sha256:
            unchanged_files.append(doc_spec.source)
            continue

        if prev_entry:
            updated_files.append(doc_spec.source)
            old_ids = prev_entry.get("chunk_ids", [])
            if old_ids:
                try:
                    collection.delete(ids=old_ids)
                except Exception:
                    pass
                deleted_chunks += len(old_ids)
        else:
            added_files.append(doc_spec.source)

        text_content = raw_bytes.decode("utf-8")
        chunks = chunk_markdown_by_headings(
            text_content,
            doc_spec,
            file_sha256,
            max_chars=max_chars,
        )

        if chunks:
            new_ids = [c.chunk_id for c in chunks]
            indexed_texts = [f"[{c.source} | {c.heading_path}]\n{c.content}" for c in chunks]
            embeddings = provider.embed_documents(indexed_texts)

            metadatas: list[dict[str, Any]] = []
            for c in chunks:
                meta: dict[str, Any] = {
                    "source": c.source,
                    "heading_path": c.heading_path,
                    "dashboard": c.dashboard,
                    "doc_type": c.doc_type,
                    "allowed_roles": ",".join(c.allowed_roles),
                    "doc_sha256": c.doc_sha256,
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                }
                for role in c.allowed_roles:
                    meta[f"role_{role}"] = True
                metadatas.append(meta)

            collection.add(
                ids=new_ids,
                documents=indexed_texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            indexed_chunks += len(chunks)
            stored_ids = new_ids
        else:
            stored_ids = []

        manifest_data["files"][doc_spec.source] = {
            "sha256": file_sha256,
            "rel_path": doc_spec.rel_path,
            "chunk_ids": stored_ids,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }

    # Write manifest back
    target_manifest.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return IngestReport(
        total_files=total_files,
        added_files=added_files,
        updated_files=updated_files,
        unchanged_files=unchanged_files,
        removed_files=removed_files,
        indexed_chunks=indexed_chunks,
        deleted_chunks=deleted_chunks,
        embedding_signature=current_sig,
    )


if __name__ == "__main__":
    report = ingest_corpus()
    print("Ingestion Completed:")
    print(f"Total files: {report.total_files}")
    print(f"Added: {report.added_files}")
    print(f"Updated: {report.updated_files}")
    print(f"Unchanged: {len(report.unchanged_files)}")
    print(f"Indexed chunks: {report.indexed_chunks}")
    print(f"Deleted chunks: {report.deleted_chunks}")
    print(f"Signature: {report.embedding_signature}")
