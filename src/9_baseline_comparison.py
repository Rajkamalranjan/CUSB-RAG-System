"""
Baseline Comparison Framework

Compare RAG system against baselines:
- LLM-only (no retrieval)
- Simple retrieval (no LLM generation)
- Different RAG configurations
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.generativeai as genai
from tqdm import tqdm

from config import GEMINI_API_KEY, REPORTS_DIR, TOP_K
from rag_engine import RAGPipeline

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

genai.configure(api_key=GEMINI_API_KEY)

# Benchmark queries
BENCHMARK_QUERIES = [
    "What is CUSB?",
    "What is the admission process?",
    "What is CUET?",
    "What is the hostel fee?",
    "What are the available courses?",
    "What is the NAAC grade of CUSB?",
    "What are the hostel facilities?",
    "How to apply for admission?",
    "What is the fee structure for UG courses?",
    "What PhD programs are available?",
    "सीयूएसबी क्या है?",
    "सीयूएसबी में प्रवेश प्रक्रिया क्या है?",
    "सीयूईटी क्या है?",
    "हॉस्टल फीस कितनी है?",
    "उपलब्ध कोर्स कौन कौन से हैं?",
    "CUSB kya hai?",
    "CUSB me admission process kya hai?",
    "hostel fee kya hai?",
    "NAAC grade kya hai CUSB ka?",
    "M.Sc Biotechnology ki fees kya hai?",
]


class BaselineComparison:
    """Compare RAG against various baselines."""

    def llm_only_baseline(self, query: str) -> dict[str, Any]:
        """
        LLM-only baseline (no retrieval).

        Args:
            query: User query

        Returns:
            Dictionary with result
        """
        start = time.perf_counter()

        try:
            model = genai.GenerativeModel("gemini-2.5-flash-lite")
            response = model.generate_content(
                f"You are a helpful assistant for CUSB (Central University of South Bihar). "
                f"Answer this question: {query}\n\n"
                f"Note: Answer based on your knowledge, without retrieval."
            )
            latency_ms = (time.perf_counter() - start) * 1000

            return {
                "query": query,
                "answer": response.text,
                "latency_ms": latency_ms,
                "sources": [],
                "baseline": "llm_only",
            }

        except Exception as e:
            return {
                "query": query,
                "answer": f"Error: {str(e)}",
                "latency_ms": (time.perf_counter() - start) * 1000,
                "sources": [],
                "baseline": "llm_only",
                "error": str(e),
            }

    def retrieval_only_baseline(self, query: str) -> dict[str, Any]:
        """
        Retrieval-only baseline (no LLM generation).

        Args:
            query: User query

        Returns:
            Dictionary with result
        """
        start = time.perf_counter()

        try:
            rag = RAGPipeline(use_llm=False)
            result = rag.answer(query, top_k=TOP_K)
            latency_ms = (time.perf_counter() - start) * 1000

            # Use retrieved context as answer
            context_parts = []
            for source in result.get("sources", [])[:3]:
                heading = source.get("heading", "Unknown")
                context_parts.append(f"{heading}: [retrieved document]")

            answer = "\n\n".join(context_parts) if context_parts else "No relevant documents found"

            return {
                "query": query,
                "answer": answer,
                "latency_ms": latency_ms,
                "sources": result.get("sources", []),
                "baseline": "retrieval_only",
            }

        except Exception as e:
            return {
                "query": query,
                "answer": f"Error: {str(e)}",
                "latency_ms": (time.perf_counter() - start) * 1000,
                "sources": [],
                "baseline": "retrieval_only",
                "error": str(e),
            }

    def rag_baseline(self, query: str) -> dict[str, Any]:
        """
        Full RAG baseline (retrieval + LLM).

        Args:
            query: User query

        Returns:
            Dictionary with result
        """
        start = time.perf_counter()

        try:
            rag = RAGPipeline(use_llm=True)
            result = rag.answer(query, top_k=TOP_K)
            latency_ms = (time.perf_counter() - start) * 1000

            return {
                "query": query,
                "answer": result.get("answer", ""),
                "latency_ms": latency_ms,
                "sources": result.get("sources", []),
                "baseline": "rag_full",
            }

        except Exception as e:
            return {
                "query": query,
                "answer": f"Error: {str(e)}",
                "latency_ms": (time.perf_counter() - start) * 1000,
                "sources": [],
                "baseline": "rag_full",
                "error": str(e),
            }

    def run_comparison(
        self,
        queries: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Run baseline comparison.

        Args:
            queries: List of queries to test

        Returns:
            Dictionary with comparison results
        """
        if queries is None:
            queries = BENCHMARK_QUERIES

        print("\n📊 BASELINE COMPARISON")
        print("=" * 80)

        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "num_queries": len(queries),
            "baselines": {},
        }

        baselines = [
            ("LLM Only", self.llm_only_baseline),
            ("Retrieval Only", self.retrieval_only_baseline),
            ("Full RAG", self.rag_baseline),
        ]

        for baseline_name, baseline_fn in baselines:
            print(f"\n🔬 Testing: {baseline_name}")
            baseline_results = []
            latencies = []

            for query in tqdm(queries, desc=f"  {baseline_name}"):
                result = baseline_fn(query)
                baseline_results.append(result)
                if "latency_ms" in result:
                    latencies.append(result["latency_ms"])

            # Calculate statistics
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            results["baselines"][baseline_name.lower().replace(" ", "_")] = {
                "results": baseline_results,
                "avg_latency_ms": avg_latency,
                "num_queries": len(baseline_results),
            }

            print(f"  ✅ Average latency: {avg_latency:.2f}ms")

        # Save results
        output_path = REPORTS_DIR / f"baseline_comparison_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(results) + "\n")

        print(f"\n✅ Comparison results saved to: {output_path}")
        return results


def main():
    """Run baseline comparison."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--queries",
        type=int,
        default=5,
        help="Number of queries to test (default: 5)"
    )
    args = parser.parse_args()

    comparison = BaselineComparison()
    comparison.run_comparison(BENCHMARK_QUERIES[:args.queries])

    print("\n" + "=" * 80)
    print("✅ Baseline comparison completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
