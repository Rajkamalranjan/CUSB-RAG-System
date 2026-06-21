"""Reciprocal Rank Fusion."""

from __future__ import annotations


def reciprocal_rank_fusion(rankings: list[list[dict]], k: int = 60) -> list[dict]:
    by_key: dict[str, dict] = {}
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            key = str(item.get("id"))
            by_key.setdefault(key, item.copy())
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    fused = []
    for key, item in by_key.items():
        item["rrf_score"] = scores[key]
        item["score"] = scores[key]
        fused.append(item)
    fused.sort(key=lambda item: item["rrf_score"], reverse=True)
    return fused

