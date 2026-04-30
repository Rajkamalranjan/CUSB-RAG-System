"""
Step 4: Evaluate retrieval quality on the QA dataset.

This lightweight research harness measures whether retrieved context contains
tokens from the reference answer. It does not judge final LLM answer quality.

Usage:
    python src/4_evaluate_retrieval.py --limit 100 --top-k 5
"""

import argparse
import json
import re
import sys
from pathlib import Path

from config import EVAL_DIR, QA_DATASET_PATH, TOP_K
from rag_engine import Retriever

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def normalize_tokens(text: str) -> set[str]:
    """Tokenize enough for reproducible retrieval diagnostics."""
    text = text.lower()
    return set(re.findall(r"[\w₹]+", text, flags=re.UNICODE))


def answer_token_recall(reference_answer: str, retrieved_context: str) -> float:
    answer_tokens = normalize_tokens(reference_answer)
    context_tokens = normalize_tokens(retrieved_context)

    answer_tokens = {token for token in answer_tokens if len(token) > 2}
    if not answer_tokens:
        return 0.0

    return len(answer_tokens & context_tokens) / len(answer_tokens)


def load_qa(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="Number of QA pairs to evaluate")
    parser.add_argument("--top-k", type=int, default=TOP_K, help="Retrieved chunks per query")
    parser.add_argument(
        "--output",
        default=str(EVAL_DIR / "retrieval_eval.jsonl"),
        help="JSONL file for per-example retrieval results",
    )
    args = parser.parse_args()

    qa_pairs = load_qa(QA_DATASET_PATH)[: args.limit]
    retriever = Retriever()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    recalls = []
    hits_at_50 = 0

    with open(output_path, "w", encoding="utf-8") as out:
        for row in qa_pairs:
            query = row["input"]
            expected = row["output"]
            chunks = retriever.retrieve(query, top_k=args.top_k)
            context = retriever.build_context(chunks)
            recall = answer_token_recall(expected, context)
            recalls.append(recall)
            hits_at_50 += recall >= 0.50

            out.write(
                json.dumps(
                    {
                        "query": query,
                        "expected": expected,
                        "answer_token_recall": recall,
                        "sources": [
                            {
                                "id": chunk.get("id"),
                                "heading": chunk["heading"],
                                "score": chunk["score"],
                            }
                            for chunk in chunks
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    mean_recall = sum(recalls) / len(recalls) if recalls else 0.0
    hit_rate = hits_at_50 / len(recalls) if recalls else 0.0

    print("Retrieval evaluation complete")
    print(f"Examples       : {len(recalls)}")
    print(f"Top-k          : {args.top_k}")
    print(f"Mean recall    : {mean_recall:.3f}")
    print(f"Hit@0.50 recall: {hit_rate:.3f}")
    print(f"Report         : {output_path}")


if __name__ == "__main__":
    main()
