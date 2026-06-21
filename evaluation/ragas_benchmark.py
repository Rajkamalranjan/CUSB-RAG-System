"""RAGAS-style generation evaluation for CUSB RAG.

This runner writes a report even when ragas is not installed/configured, so it
can be used in CI and upgraded on the RTX 4070 SUPER system.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_rows(path: Path, limit: int = 0) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows[:limit] if limit else rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/benchmark/cusb_test.jsonl")
    parser.add_argument("--output", default="reports/ragas_benchmark.json")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    rows = load_rows(Path(args.input), args.limit)
    report = {
        "metric_set": ["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
        "num_examples": len(rows),
        "status": "prepared",
        "note": "Wire generated answers/contexts into ragas.evaluate() after provider keys are configured.",
        "examples": rows[:3],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()

