"""Load current chunk pickle into Qdrant."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from embeddings.embed_pipeline import EmbeddingPipeline
from vectorstore.collection_manager import chunk_payload
from vectorstore.qdrant_client import QdrantVectorStore


def load_chunks_to_qdrant(
    chunks_path: Path = Path("data/cusb_chunks.pkl"),
    embeddings_path: Path = Path("data/cusb_embeddings.npy"),
    batch_size: int = 256,
) -> None:
    with chunks_path.open("rb") as f:
        chunks = pickle.load(f)

    if embeddings_path.exists():
        cached_vectors = np.load(embeddings_path)
        if len(cached_vectors) == len(chunks):
            vectors = cached_vectors.astype("float32")
            print(f"Using cached embeddings: {embeddings_path}")
        else:
            print(
                f"Ignoring cached embeddings: {len(cached_vectors)} vectors for {len(chunks)} chunks"
            )
            vectors = None
    else:
        vectors = None

    if vectors is None:
        embedder = EmbeddingPipeline()
        vectors = embedder.encode([chunk["text"] for chunk in chunks]).astype("float32")

    store = QdrantVectorStore()

    try:
        total = len(chunks)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_chunks = chunks[start:end]
            store.upsert(
                ids=[int(chunk.get("id", idx)) for idx, chunk in enumerate(batch_chunks, start)],
                vectors=vectors[start:end].tolist(),
                payloads=[chunk_payload(chunk) for chunk in batch_chunks],
            )
            print(f"Indexed {end}/{total} chunks into Qdrant", flush=True)
    finally:
        store.close()
