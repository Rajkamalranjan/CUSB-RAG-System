"""
Step 5: Benchmark the RAG pipeline on a fixed multilingual query suite.

Usage:
    python src/5_benchmark_rag.py --no-llm
    python src/5_benchmark_rag.py
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from config import (
    EMBED_MODEL,
    GEMINI_MODEL,
    REPORTS_DIR,
    RETRIEVAL_CANDIDATES,
    TOP_K,
    USE_RERANKER,
)
from rag_engine import RAGPipeline

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BENCHMARK_QUERIES = [
    "What is CUSB?",
    "What is the admission process?",
    "What is CUET?",
    "What is the hostel fee?",
    "सीयूएसबी क्या है?",
    "सीयूएसबी में प्रवेश प्रक्रिया क्या है?",
    "सीयूईटी क्या है?",
    "CUSB kya hai?",
    "CUSB me admission process kya hai?",
    "hostel fee kya hai?",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="Benchmark retrieval/fallback only")
    parser.add_argument("--output", default=None, help="Optional JSONL output path")
    parser.add_argument("--delay", type=int, default=5, help="Seconds between queries to avoid rate limits (default: 5)")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output) if args.output else REPORTS_DIR / f"rag_benchmark_{timestamp}.jsonl"

    rag = RAGPipeline(use_llm=not args.no_llm)

    rows = []
    for i, query in enumerate(BENCHMARK_QUERIES):
        started = time.perf_counter()
        result = rag.answer(query, top_k=TOP_K)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        row = {
            "query": query,
            "language": result["language"],
            "latency_ms": latency_ms,
            "answer": result["answer"],
            "sources": result["sources"],
            "context": result["context"],
        }
        rows.append(row)
        print(f"[{latency_ms:>8.2f} ms] {query} -> {result['language']}")

        # Delay between queries to avoid rate limiting
        if not args.no_llm and i < len(BENCHMARK_QUERIES) - 1:
            print(f"   ⏳ Waiting {args.delay}s to avoid rate limit...")
            time.sleep(args.delay)

    metadata = {
        "type": "metadata",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "use_llm": not args.no_llm,
        "top_k": TOP_K,
        "embedding_model": EMBED_MODEL,
        "gemini_model": GEMINI_MODEL,
        "retrieval_candidates": RETRIEVAL_CANDIDATES,
        "use_reranker": USE_RERANKER,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    avg_latency = sum(row["latency_ms"] for row in rows) / len(rows)
    print("\nBenchmark complete")
    print(f"Queries        : {len(rows)}")
    print(f"Average latency: {avg_latency:.2f} ms")
    print(f"Report         : {output_path}")


if __name__ == "__main__":
    main()
