"""BGE cross-encoder reranker wrapper."""

from __future__ import annotations

import os


class BGEReranker:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("RERANK_MODEL", "BAAI/bge-reranker-base")
        self.model = None
        try:
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(self.model_name, device=os.getenv("RERANK_DEVICE", "cuda"))
        except Exception:
            try:
                from sentence_transformers import CrossEncoder

                self.model = CrossEncoder(self.model_name)
            except Exception:
                self.model = None

    def rerank(self, query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
        if not self.model or not chunks:
            return chunks[:top_k]
        pairs = [[query, chunk.get("text", "")[:1600]] for chunk in chunks]
        scores = self.model.predict(pairs)
        reranked = []
        for chunk, score in zip(chunks, scores):
            item = chunk.copy()
            item["pre_rerank_score"] = item.get("score", 0.0)
            item["rerank_score"] = float(score)
            item["score"] = float(score)
            reranked.append(item)
        reranked.sort(key=lambda item: item["score"], reverse=True)
        return reranked[:top_k]

