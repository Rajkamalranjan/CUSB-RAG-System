"""Create leakage-free benchmark splits for IEEE-style RAG evaluation.

The existing project can include QA pairs inside the vector index, which is good
for chatbot recall but optimistic for research claims. This script creates
train/validation/test JSONL files and an unanswerable set so experiments can
report held-out performance transparently.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Iterable

from config import QA_DATASET_PATH
from research_config import CONFIG, benchmark_path, ensure_research_dirs

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


UNANSWERABLE_QUERIES = [
    "What is today's exact hostel room availability?",
    "Who will win the next CUSB student election?",
    "What is my personal application status?",
    "Give me the private phone number of a faculty member.",
    "What is the unpublished cutoff for next year?",
    "Can you guarantee my admission?",
    "What is the exact mess menu for tomorrow?",
    "Show confidential student records.",
    "What is the latest notice if it is not in the knowledge base?",
    "Tell me a fee waiver decision for my personal case.",
]


def load_qa(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    cleaned = []
    for index, row in enumerate(rows):
        question = str(row.get("input", "")).strip()
        answer = str(row.get("output", "")).strip()
        if question and answer:
            cleaned.append(
                {
                    "id": f"qa_{index:05d}",
                    "question": question,
                    "reference_answer": answer,
                    "answerable": True,
                    "source": "final_data_set.json",
                }
            )
    return cleaned


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def make_splits(rows: list[dict]) -> dict[str, list[dict]]:
    rng = random.Random(CONFIG.random_seed)
    shuffled = rows[:]
    rng.shuffle(shuffled)

    total = len(shuffled)
    train_end = int(total * CONFIG.train_ratio)
    validation_end = train_end + int(total * CONFIG.validation_ratio)

    splits = {
        "train": shuffled[:train_end],
        "validation": shuffled[train_end:validation_end],
        "test": shuffled[validation_end:],
    }
    splits["unanswerable"] = [
        {
            "id": f"unanswerable_{i:03d}",
            "question": question,
            "reference_answer": (
                "The knowledge base does not contain enough verified information "
                "to answer this question."
            ),
            "answerable": False,
            "source": "curated_unanswerable",
        }
        for i, question in enumerate(UNANSWERABLE_QUERIES, 1)
    ]
    return splits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(QA_DATASET_PATH), help="QA dataset JSON path")
    args = parser.parse_args()

    ensure_research_dirs()
    rows = load_qa(Path(args.input))
    splits = make_splits(rows)

    print("Creating leakage-free CUSB benchmark splits")
    for split, split_rows in splits.items():
        count = write_jsonl(benchmark_path(split), split_rows)
        print(f"  {split:12s}: {count:4d} -> {benchmark_path(split)}")

    metadata = {
        "project": CONFIG.project_name,
        "random_seed": CONFIG.random_seed,
        "total_answerable": len(rows),
        "train_ratio": CONFIG.train_ratio,
        "validation_ratio": CONFIG.validation_ratio,
        "test_ratio": CONFIG.test_ratio,
        "warning": (
            "For formal results, rebuild the vector index with --exclude-qa or "
            "index only the training/corpus documents, never the held-out test rows."
        ),
    }
    write_jsonl(benchmark_path("metadata"), [metadata])
    print("Done. Use the test and unanswerable splits for paper claims.")


if __name__ == "__main__":
    main()
