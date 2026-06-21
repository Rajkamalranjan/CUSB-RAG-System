"""Hybrid retrieval for research-grade CUSB EduRAG experiments.

Combines the existing dense FAISS retriever with BM25 lexical retrieval and
Reciprocal Rank Fusion (RRF). This is a strong baseline for IEEE-style RAG
papers because it compares and combines semantic and exact-token matching.
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from typing import Iterable

from rag_engine import Retriever, expand_query_for_retrieval
from research_config import CONFIG

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


TOKEN_PATTERN = re.compile(r"[\w]+", flags=re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text) if len(token) > 1]


def reciprocal_rank_fusion(rankings: Iterable[list[dict]], rrf_k: int = CONFIG.rrf_k) -> dict[int, float]:
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            item_id = int(item["id"])
            fused[item_id] = fused.get(item_id, 0.0) + 1.0 / (rrf_k + rank)
    return fused


@dataclass
class RetrievalMetrics:
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    factual_token_recall: float


class BM25Lite:
    """Small dependency-free BM25 implementation for reproducible experiments."""

    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.doc_count = len(documents)
        self.doc_lengths = [len(doc) for doc in documents]
        self.avg_doc_length = sum(self.doc_lengths) / max(1, self.doc_count)
        self.doc_freq: dict[str, int] = {}
        self.term_freqs: list[dict[str, int]] = []

        for doc in documents:
            freqs: dict[str, int] = {}
            for token in doc:
                freqs[token] = freqs.get(token, 0) + 1
            self.term_freqs.append(freqs)
            for token in freqs:
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1

    def idf(self, token: str) -> float:
        freq = self.doc_freq.get(token, 0)
        return math.log(1 + (self.doc_count - freq + 0.5) / (freq + 0.5))

    def score(self, query_tokens: list[str], index: int) -> float:
        score = 0.0
        freqs = self.term_freqs[index]
        doc_len = self.doc_lengths[index]
        for token in query_tokens:
            tf = freqs.get(token, 0)
            if tf == 0:
                continue
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
            score += self.idf(token) * (tf * (self.k1 + 1)) / denominator
        return score

    def search(self, query: str, top_k: int) -> list[dict]:
        query_tokens = tokenize(query)
        scored = []
        for index in range(self.doc_count):
            score = self.score(query_tokens, index)
            if score > 0:
                scored.append({"id": index, "bm25_score": float(score)})
        scored.sort(key=lambda item: item["bm25_score"], reverse=True)
        return scored[:top_k]


class HybridRetriever:
    """Dense + BM25 + RRF retrieval over the current CUSB chunks."""

    def __init__(self):
        self.dense = Retriever()
        corpus = [
            tokenize(f"{chunk.get('heading', '')} {chunk.get('text', '')}")
            for chunk in self.dense.chunks
        ]
        self.bm25 = BM25Lite(corpus)

    def retrieve(self, query: str, top_k: int = CONFIG.final_top_k) -> list[dict]:
        expanded_query = expand_query_for_retrieval(query)
        dense_results = self.dense.retrieve(expanded_query, top_k=CONFIG.dense_top_k)
        bm25_results = self.bm25.search(expanded_query, top_k=CONFIG.bm25_top_k)

        dense_ranking = [
            {"id": chunk["id"], "dense_score": chunk.get("score", 0.0)}
            for chunk in dense_results
        ]
        fused_scores = reciprocal_rank_fusion([dense_ranking, bm25_results])
        by_id = {int(chunk["id"]): chunk.copy() for chunk in self.dense.chunks}

        results = []
        for item_id, score in fused_scores.items():
            chunk = by_id[item_id]
            chunk["score"] = float(score)
            chunk["rrf_score"] = float(score)
            results.append(chunk)

        results.sort(key=lambda item: item["rrf_score"], reverse=True)
        return results[:top_k]

    def build_context(self, chunks: list[dict], max_chars: int | None = None) -> str:
        return self.dense.build_context(chunks, max_chars=max_chars or 3000)


def factual_token_recall(reference: str, context: str) -> float:
    reference_tokens = {token for token in tokenize(reference) if len(token) > 2}
    if not reference_tokens:
        return 0.0
    context_tokens = set(tokenize(context))
    return len(reference_tokens & context_tokens) / len(reference_tokens)


def retrieval_metrics(reference_answer: str, chunks: list[dict], context: str) -> RetrievalMetrics:
    recall = factual_token_recall(reference_answer, context)
    relevance_by_rank = []
    reference_tokens = {token for token in tokenize(reference_answer) if len(token) > 2}
    for chunk in chunks:
        chunk_tokens = set(tokenize(f"{chunk.get('heading', '')} {chunk.get('text', '')}"))
        overlap = len(reference_tokens & chunk_tokens) / max(1, len(reference_tokens))
        relevance_by_rank.append(overlap)

    first_relevant = next((i + 1 for i, value in enumerate(relevance_by_rank) if value >= 0.20), None)
    mrr = 1.0 / first_relevant if first_relevant else 0.0

    dcg = sum(value / math.log2(rank + 2) for rank, value in enumerate(relevance_by_rank))
    ideal = sorted(relevance_by_rank, reverse=True)
    idcg = sum(value / math.log2(rank + 2) for rank, value in enumerate(ideal))
    ndcg = dcg / idcg if idcg else 0.0

    return RetrievalMetrics(
        recall_at_k=1.0 if recall >= CONFIG.factual_overlap_threshold else 0.0,
        mrr=mrr,
        ndcg_at_k=ndcg,
        factual_token_recall=recall,
    )
