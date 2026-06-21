"""BM25 sparse retriever for exact CUSB terms."""

from __future__ import annotations

import re

TOKEN_PATTERN = re.compile(r"[\w]+", flags=re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token) > 1]


class BM25Retriever:
    def __init__(self, chunks: list[dict]):
        from rank_bm25 import BM25Okapi

        self.chunks = chunks
        self.corpus_tokens = [tokenize(f"{chunk.get('heading', '')} {chunk.get('text', '')}") for chunk in chunks]
        self.index = BM25Okapi(self.corpus_tokens)

    def retrieve(self, query: str, top_k: int = 20) -> list[dict]:
        tokens = tokenize(query)
        scores = self.index.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)[:top_k]
        results = []
        for idx, score in ranked:
            if score <= 0:
                continue
            chunk = self.chunks[idx].copy()
            chunk["bm25_score"] = float(score)
            chunk["score"] = float(score)
            results.append(chunk)
        return results

