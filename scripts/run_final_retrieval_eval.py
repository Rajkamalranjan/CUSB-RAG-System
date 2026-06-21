"""Run the final 50-question retrieval smoke test.

This writes source rankings without calling the LLM, so it is cheap and
repeatable even when API quota is exhausted.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_engine import RAGPipeline


def main() -> None:
    input_path = ROOT / "eval" / "final_50_questions.jsonl"
    output_path = ROOT / "reports" / f"final_retrieval_eval_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pipeline = RAGPipeline(use_llm=False)
    total = 0
    with input_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as out:
        for line in src:
            if not line.strip():
                continue
            row = json.loads(line)
            result = pipeline.answer(row["question"])
            record = {
                **row,
                "sources": result["sources"],
                "top_heading": result["sources"][0]["heading"] if result["sources"] else None,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            total += 1

    print(f"Wrote {total} retrieval records to {output_path}")


if __name__ == "__main__":
    main()
