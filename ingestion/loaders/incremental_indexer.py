"""No-Docker incremental indexing for uploaded CUSB PDFs."""

from __future__ import annotations

import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from embeddings.embed_pipeline import EmbeddingPipeline
from ingestion.extractors.pdf_extractor import extract_pdf_text
from ingestion.processors.deduplicator import deduplicate
from ingestion.processors.metadata_enricher import enrich
from vectorstore.collection_manager import chunk_payload
from vectorstore.qdrant_client import QdrantVectorStore


CHUNKS_PATH = Path("data/cusb_chunks.pkl")
EMBEDDINGS_PATH = Path("data/cusb_embeddings.npy")
MANIFEST_PATH = Path("data/index_manifest.json")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"documents": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _save_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_chunks() -> list[dict[str, Any]]:
    if not CHUNKS_PATH.exists():
        return []
    with CHUNKS_PATH.open("rb") as f:
        return pickle.load(f)


def _save_chunks(chunks: list[dict[str, Any]]) -> None:
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CHUNKS_PATH.open("wb") as f:
        pickle.dump(chunks, f)


def _split_page(page: dict[str, Any], max_chars: int = 1800, overlap: int = 250) -> list[dict[str, Any]]:
    text = " ".join(str(page.get("text", "")).split())
    if not text:
        return []
    chunks = []
    start = 0
    part = 1
    while start < len(text):
        end = min(len(text), start + max_chars)
        piece = text[start:end].strip()
        if piece:
            chunks.append(
                {
                    "heading": f"{Path(page.get('source_file', 'upload')).name} page {page.get('page')} part {part}",
                    "text": piece,
                    "char_count": len(piece),
                    "source_file": page.get("source_file"),
                    "page": page.get("page"),
                    "category": "upload",
                }
            )
        if end >= len(text):
            break
        start = max(0, end - overlap)
        part += 1
    return chunks


def index_pdf_incremental(path: str | Path) -> dict[str, Any]:
    pdf_path = Path(path)
    if not pdf_path.exists():
        return {"status": "failed", "error": f"file not found: {pdf_path}"}

    manifest = _load_manifest()
    digest = _file_sha256(pdf_path)
    key = str(pdf_path)
    previous = manifest["documents"].get(key)
    if previous and previous.get("sha256") == digest:
        return {"status": "unchanged", "file": key, "chunks_added": 0}

    existing_chunks = _load_chunks()
    start_id = max((int(chunk.get("id", -1)) for chunk in existing_chunks), default=-1) + 1

    pages = extract_pdf_text(pdf_path)
    new_chunks = []
    for page in pages:
        for chunk in _split_page(page):
            new_chunks.append(enrich(chunk, category="upload"))
    new_chunks = deduplicate(new_chunks)
    for offset, chunk in enumerate(new_chunks):
        chunk["id"] = start_id + offset
        chunk["content_sha256"] = digest
        chunk["indexed_at_utc"] = datetime.now(timezone.utc).isoformat()

    if not new_chunks:
        return {"status": "empty", "file": key, "chunks_added": 0}

    embedder = EmbeddingPipeline()
    vectors = embedder.encode([chunk["text"] for chunk in new_chunks]).astype("float32")

    store = QdrantVectorStore()
    try:
        store.upsert(
            ids=[int(chunk["id"]) for chunk in new_chunks],
            vectors=vectors.tolist(),
            payloads=[chunk_payload(chunk) for chunk in new_chunks],
        )
    finally:
        store.close()

    all_chunks = existing_chunks + new_chunks
    _save_chunks(all_chunks)

    if EMBEDDINGS_PATH.exists():
        old_vectors = np.load(EMBEDDINGS_PATH).astype("float32")
        if len(old_vectors) == len(existing_chunks):
            np.save(EMBEDDINGS_PATH, np.vstack([old_vectors, vectors]))

    manifest["documents"][key] = {
        "sha256": digest,
        "chunk_ids": [chunk["id"] for chunk in new_chunks],
        "chunks": len(new_chunks),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _save_manifest(manifest)
    return {"status": "indexed", "file": key, "chunks_added": len(new_chunks)}


def delete_document(source_file: str) -> dict[str, Any]:
    chunks = _load_chunks()
    keep = [chunk for chunk in chunks if str(chunk.get("source_file")) != source_file]
    removed = len(chunks) - len(keep)
    if removed:
        _save_chunks(keep)

    store = QdrantVectorStore()
    try:
        deleted = store.delete_by_source(source_file)
    finally:
        store.close()

    manifest = _load_manifest()
    manifest["documents"].pop(source_file, None)
    _save_manifest(manifest)
    return {"status": "deleted", "source_file": source_file, "chunks_removed": removed, "qdrant": deleted}
