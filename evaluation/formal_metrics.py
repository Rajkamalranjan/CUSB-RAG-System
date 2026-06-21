"""Formal retrieval and hallucination metrics for CUSB RAG."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_engine import RAGPipeline


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def reciprocal_rank(sources: list[dict], golden_id) -> float:
    if golden_id is None:
        return 0.0
    for index, source in enumerate(sources, 1):
        if str(source.get("id")) == str(golden_id) or str(source.get("chunk_id")) == str(golden_id):
            return 1.0 / index
    return 0.0


def hit_at(sources: list[dict], golden_id, k: int) -> float:
    if golden_id is None:
        return 0.0
    return float(any(str(source.get("id")) == str(golden_id) or str(source.get("chunk_id")) == str(golden_id) for source in sources[:k]))


def summarize(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "mean": 0.0}
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/benchmark/cusb_test.jsonl")
    parser.add_argument("--output", default="reports/formal_metrics.json")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--llm", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))[: args.limit]
    pipeline = RAGPipeline(use_llm=args.llm)
    hit1 = []
    hit5 = []
    mrr10 = []
    latency = []
    hallucination_flags = []
    per_query = []

    for row in rows:
        question = row.get("question") or row.get("query") or row.get("input")
        if not question:
            continue
        golden_id = row.get("golden_passage_id") or row.get("chunk_id")
        started = time.perf_counter()
        result = pipeline.answer(question, top_k=10)
        elapsed = (time.perf_counter() - started) * 1000
        sources = result.get("sources", [])
        answer = result.get("answer", "")
        not_found_expected = row.get("answerable") is False
        hallucinated = bool(not_found_expected and "not include" not in answer.lower() and "could not find" not in answer.lower())

        hit1.append(hit_at(sources, golden_id, 1))
        hit5.append(hit_at(sources, golden_id, 5))
        mrr10.append(reciprocal_rank(sources[:10], golden_id))
        latency.append(elapsed)
        hallucination_flags.append(float(hallucinated))
        per_query.append(
            {
                "id": row.get("id"),
                "question": question,
                "golden_passage_id": golden_id,
                "hit_at_1": hit1[-1],
                "hit_at_5": hit5[-1],
                "mrr_at_10": mrr10[-1],
                "latency_ms": round(elapsed, 2),
                "hallucinated": hallucinated,
                "top_sources": sources[:5],
            }
        )

    report = {
        "num_queries": len(per_query),
        "metrics": {
            "hit_at_1": summarize(hit1),
            "hit_at_5": summarize(hit5),
            "mrr_at_10": summarize(mrr10),
            "latency_ms": summarize(latency),
            "hallucination_rate": summarize(hallucination_flags),
        },
        "per_query": per_query,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
