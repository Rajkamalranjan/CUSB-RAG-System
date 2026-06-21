"""GPU-aware embedding generation pipeline."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from embeddings.cache_manager import EmbeddingCache


class EmbeddingPipeline:
    def __init__(
        self,
        model_name: str | None = None,
        batch_size: int | None = None,
        cache_path: str | Path = "data/embedding_cache.json",
    ):
        self.model_name = model_name or os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
        self.batch_size = batch_size or int(os.getenv("EMBED_BATCH_SIZE", "64"))
        self.cache = EmbeddingCache(Path(cache_path))
        from sentence_transformers import SentenceTransformer

        device = os.getenv("EMBED_DEVICE", "cuda")
        try:
            self.model = SentenceTransformer(self.model_name, device=device)
        except Exception:
            self.model = SentenceTransformer(self.model_name)

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        prefix = "query: " if is_query and "e5" in self.model_name.lower() else "passage: " if "e5" in self.model_name.lower() else ""
        prepared = [prefix + text for text in texts]
        vectors = self.model.encode(
            prepared,
            batch_size=self.batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vectors.astype("float32")

