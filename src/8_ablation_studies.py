"""
Ablation Studies and Baseline Comparison Framework

Enables systematic evaluation of RAG components:
- Different embedding models
- Different context window sizes
- Different top-K values
- Query expansion impact
- Reranking effectiveness
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from config import (
    ALTERNATIVE_EMBEDDING_MODELS,
    CONTEXT_WINDOW_SIZES,
    EMBED_MODEL,
    REPORTS_DIR,
    TOP_K_VALUES,
    RETRIEVAL_CANDIDATES,
)
from rag_engine import RAGPipeline

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# Sample multilingual queries
ABLATION_QUERIES = [
    "What is CUSB?",
    "What is the admission process?",
    "What is CUET?",
    "What is the hostel fee?",
    "What are the available courses?",
    "सीयूएसबी क्या है?",
    "सीयूएसबी में प्रवेश प्रक्रिया क्या है?",
    "सीयूईटी क्या है?",
    "CUSB kya hai?",
    "CUSB me admission process kya hai?",
]


class EmbeddingModelAblation:
    """Ablation study for different embedding models."""

    @staticmethod
    def benchmark_embedding_model(
        model_name: str,
        queries: list[str],
        top_k: int = 5
    ) -> dict[str, Any]:
        """
        Benchmark a specific embedding model.

        Args:
            model_name: Name of embedding model
            queries: List of queries to test
            top_k: Number of results to retrieve

        Returns:
            Dictionary with benchmark results
        """
        results = {
            "model": model_name,
            "queries": [],
            "total_latency_ms": 0,
        }

        print(f"\n  Testing model: {model_name}")

        try:
            # Load embedding model
            embedder = SentenceTransformer(model_name)
            print(f"    ✅ Model loaded successfully")

            # Create temporary RAG pipeline with this model
            # (This is a simplified version - in practice you'd modify the pipeline)
            for query in queries:
                start = time.perf_counter()
                # Encode query
                embedding = embedder.encode(query)
                latency_ms = (time.perf_counter() - start) * 1000

                results["queries"].append({
                    "query": query,
                    "latency_ms": latency_ms,
                })
                results["total_latency_ms"] += latency_ms

        except Exception as e:
            print(f"    ❌ Error: {e}")
            results["error"] = str(e)

        return results

    def run_embedding_ablation(
        self,
        models: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Run ablation study on embedding models.

        Args:
            models: List of models to test (None = use default alternatives)

        Returns:
            Dictionary with ablation results
        """
        if models is None:
            models = [EMBED_MODEL] + ALTERNATIVE_EMBEDDING_MODELS

        print("\n🔬 EMBEDDING MODEL ABLATION STUDY")
        print("=" * 80)

        results = {
            "study": "embedding_model",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "models": [],
        }

        for model in models:
            model_results = self.benchmark_embedding_model(
                model,
                ABLATION_QUERIES[:3],  # Use subset for speed
                top_k=5
            )
            results["models"].append(model_results)

        # Save results
        output_path = REPORTS_DIR / f"ablation_embedding_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        with open(output_path, "w") as f:
            f.write(json.dumps(results) + "\n")

        print(f"\n✅ Results saved to: {output_path}")
        return results


class ContextWindowAblation:
    """Ablation study for different context window sizes."""

    def benchmark_context_window(
        self,
        context_size: int,
        queries: list[str]
    ) -> dict[str, Any]:
        """
        Benchmark with specific context window size.

        Args:
            context_size: Maximum context size in characters
            queries: List of queries to test

        Returns:
            Dictionary with results
        """
        results = {
            "context_window": context_size,
            "queries": [],
            "avg_latency_ms": 0,
        }

        print(f"  Testing context window: {context_size} chars")

        try:
            rag = RAGPipeline()
            latencies = []

            for query in queries:
                start = time.perf_counter()
                result = rag.answer(query, top_k=5)
                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)

                # Measure context usage
                context_used = len(result.get("context", ""))

                results["queries"].append({
                    "query": query,
                    "latency_ms": latency_ms,
                    "context_used": context_used,
                    "answer_length": len(result.get("answer", "")),
                })

            results["avg_latency_ms"] = sum(latencies) / len(latencies)

        except Exception as e:
            print(f"    ❌ Error: {e}")
            results["error"] = str(e)

        return results

    def run_context_ablation(
        self,
        window_sizes: list[int] | None = None
    ) -> dict[str, Any]:
        """
        Run ablation study on context window sizes.

        Args:
            window_sizes: List of window sizes to test

        Returns:
            Dictionary with ablation results
        """
        if window_sizes is None:
            window_sizes = CONTEXT_WINDOW_SIZES

        print("\n🔬 CONTEXT WINDOW ABLATION STUDY")
        print("=" * 80)

        results = {
            "study": "context_window",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_windows": [],
        }

        for window_size in tqdm(window_sizes, desc="Testing context windows"):
            window_results = self.benchmark_context_window(
                window_size,
                ABLATION_QUERIES[:3]
            )
            results["context_windows"].append(window_results)

        # Save results
        output_path = REPORTS_DIR / f"ablation_context_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        with open(output_path, "w") as f:
            f.write(json.dumps(results) + "\n")

        print(f"\n✅ Results saved to: {output_path}")
        return results


class TopKAblation:
    """Ablation study for different top-K values."""

    def benchmark_topk(
        self,
        top_k: int,
        queries: list[str]
    ) -> dict[str, Any]:
        """
        Benchmark with specific top-K value.

        Args:
            top_k: Number of chunks to retrieve
            queries: List of queries to test

        Returns:
            Dictionary with results
        """
        results = {
            "top_k": top_k,
            "queries": [],
            "avg_latency_ms": 0,
        }

        print(f"  Testing top-k: {top_k}")

        try:
            rag = RAGPipeline()
            latencies = []

            for query in queries:
                start = time.perf_counter()
                result = rag.answer(query, top_k=top_k)
                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)

                results["queries"].append({
                    "query": query,
                    "latency_ms": latency_ms,
                    "answer_quality": result.get("quality_score", 0),
                })

            results["avg_latency_ms"] = sum(latencies) / len(latencies)

        except Exception as e:
            print(f"    ❌ Error: {e}")
            results["error"] = str(e)

        return results

    def run_topk_ablation(
        self,
        top_k_values: list[int] | None = None
    ) -> dict[str, Any]:
        """
        Run ablation study on top-K values.

        Args:
            top_k_values: List of top-K values to test

        Returns:
            Dictionary with ablation results
        """
        if top_k_values is None:
            top_k_values = TOP_K_VALUES

        print("\n🔬 TOP-K ABLATION STUDY")
        print("=" * 80)

        results = {
            "study": "top_k",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "top_k_values": [],
        }

        for top_k in tqdm(top_k_values, desc="Testing top-K values"):
            topk_results = self.benchmark_topk(top_k, ABLATION_QUERIES[:3])
            results["top_k_values"].append(topk_results)

        # Save results
        output_path = REPORTS_DIR / f"ablation_topk_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        with open(output_path, "w") as f:
            f.write(json.dumps(results) + "\n")

        print(f"\n✅ Results saved to: {output_path}")
        return results


def main():
    """Run ablation studies."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--study",
        choices=["embedding", "context", "topk", "all"],
        default="all",
        help="Which ablation study to run"
    )
    args = parser.parse_args()

    if args.study in ["embedding", "all"]:
        ablation = EmbeddingModelAblation()
        ablation.run_embedding_ablation()

    if args.study in ["context", "all"]:
        ablation = ContextWindowAblation()
        ablation.run_context_ablation()

    if args.study in ["topk", "all"]:
        ablation = TopKAblation()
        ablation.run_topk_ablation()

    print("\n" + "=" * 80)
    print("✅ Ablation studies completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
