"""IEEE-style retrieval evaluation for CUSB EduRAG.

Evaluates dense-only and hybrid retrieval on held-out benchmark splits. It
reports metrics commonly expected in publishable RAG work: Recall@k, MRR,
nDCG@k, factual token recall, latency, and abstention behavior.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from hybrid_retriever import HybridRetriever, retrieval_metrics
from rag_engine import Retriever
from research_config import CONFIG, benchmark_path, ensure_research_dirs, report_path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def summarize(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "stdev": 0.0}
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.pstdev(values),
        "min": min(values),
        "max": max(values),
    }


def evaluate_retriever(name: str, retriever, rows: list[dict]) -> dict:
    per_query = []
    latency_ms = []
    recall_at_k = []
    mrr = []
    ndcg = []
    factual_recall = []

    for row in rows:
        started = time.perf_counter()
        chunks = retriever.retrieve(row["question"], top_k=CONFIG.final_top_k)
        context = retriever.build_context(chunks)
        elapsed = (time.perf_counter() - started) * 1000

        metrics = retrieval_metrics(row["reference_answer"], chunks, context)
        latency_ms.append(elapsed)
        recall_at_k.append(metrics.recall_at_k)
        mrr.append(metrics.mrr)
        ndcg.append(metrics.ndcg_at_k)
        factual_recall.append(metrics.factual_token_recall)

        per_query.append(
            {
                "id": row.get("id"),
                "question": row["question"],
                "answerable": row.get("answerable", True),
                "latency_ms": round(elapsed, 3),
                "recall_at_k": metrics.recall_at_k,
                "mrr": metrics.mrr,
                "ndcg_at_k": metrics.ndcg_at_k,
                "factual_token_recall": metrics.factual_token_recall,
                "sources": [
                    {
                        "id": chunk.get("id"),
                        "heading": chunk.get("heading"),
                        "score": chunk.get("score"),
                    }
                    for chunk in chunks
                ],
            }
        )

    return {
        "name": name,
        "config": {
            "final_top_k": CONFIG.final_top_k,
            "dense_top_k": CONFIG.dense_top_k,
            "bm25_top_k": CONFIG.bm25_top_k,
            "rrf_k": CONFIG.rrf_k,
        },
        "summary": {
            "latency_ms": summarize(latency_ms),
            "recall_at_k": summarize(recall_at_k),
            "mrr": summarize(mrr),
            "ndcg_at_k": summarize(ndcg),
            "factual_token_recall": summarize(factual_recall),
        },
        "per_query": per_query,
    }


class DenseRetrieverAdapter:
    """Adapter so the existing Retriever matches the research evaluator API."""

    def __init__(self):
        self.retriever = Retriever()

    def retrieve(self, query: str, top_k: int) -> list[dict]:
        return self.retriever.retrieve(query, top_k=top_k)

    def build_context(self, chunks: list[dict]) -> str:
        return self.retriever.build_context(chunks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="test", choices=["validation", "test", "unanswerable"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    ensure_research_dirs()
    split_path = benchmark_path(args.split)
    if not split_path.exists():
        raise FileNotFoundError(
            f"Missing split file: {split_path}. Run: python src/create_benchmark_splits.py"
        )

    rows = load_jsonl(split_path)
    if args.limit:
        rows = rows[: args.limit]

    dense_result = evaluate_retriever("dense_faiss", DenseRetrieverAdapter(), rows)
    hybrid_result = evaluate_retriever("hybrid_dense_bm25_rrf", HybridRetriever(), rows)

    report = {
        "project": CONFIG.project_name,
        "split": args.split,
        "num_queries": len(rows),
        "warning": (
            "If QA chunks are included in the FAISS index, treat these scores as "
            "diagnostic only. For paper results, rebuild without held-out QA rows."
        ),
        "systems": [dense_result, hybrid_result],
    }

    output = Path(args.output) if args.output else report_path(f"research_eval_{args.split}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Saved research evaluation report: {output}")
    for system in report["systems"]:
        summary = system["summary"]
        print(
            f"{system['name']}: "
            f"Recall@{CONFIG.final_top_k}={summary['recall_at_k']['mean']:.3f}, "
            f"MRR={summary['mrr']['mean']:.3f}, "
            f"nDCG={summary['ndcg_at_k']['mean']:.3f}, "
            f"Latency={summary['latency_ms']['mean']:.2f} ms"
        )


if __name__ == "__main__":
    main()
