"""Generate and freeze a second-form 250-question blind evaluation set.

Run this once after development and validation tuning is complete. Do not tune
backend rules against the generated questions before reporting the blind score.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


OUTPUT = Path("evaluation/final_blind_questions.jsonl")
VALIDATION_SET = Path("evaluation/heldout_unseen_questions.jsonl")
DEV_SET = Path("evaluation/research_1000_questions.jsonl")


ENGLISH_FRAMES = {
    "unseen_paraphrase": (
        "Please answer this using verified CUSB information: {query}",
        "A student needs an official CUSB answer: {query}",
        "Using the available university records, could you clarify this: {query}",
    ),
    "long_multi_intent": (
        "Please give a complete CUSB response and cover every requested point. {query}",
        "A student needs a practical answer based on official university information. {query}",
        "Using verified CUSB records, respond to all parts of this request. {query}",
    ),
    "typo_vague": (
        "{query} - official info pls",
        "{query} need cusb info",
        "{query} pls help",
    ),
    "out_of_domain": (
        "Can the CUSB assistant handle this request: {query}",
        "Please help me with this request: {query}",
        "I want the university chatbot to do this: {query}",
    ),
}

HINGLISH_FRAMES = {
    "unseen_paraphrase": (
        "Verified CUSB information ke basis par batao: {query}",
        "Official university data se answer do: {query}",
        "CUSB records check karke clarify karo: {query}",
    ),
    "long_multi_intent": (
        "Official CUSB information ke basis par sabhi points cover karo. {query}",
        "Student ke liye complete practical answer do. {query}",
        "Verified university records use karke har point ka answer do. {query}",
    ),
    "typo_vague": (
        "{query} plz",
        "{query} cusb info chahiye",
        "{query} jaldi btao",
    ),
    "out_of_domain": (
        "CUSB chatbot se yeh help chahiye: {query}",
        "University assistant yeh kar do: {query}",
        "Mujhe is request me help chahiye: {query}",
    ),
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _known_queries(*paths: Path) -> set[str]:
    queries: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        queries.update(str(row["query"]).strip().lower() for row in _read_jsonl(path))
    return queries


def generate() -> list[dict[str, Any]]:
    if not VALIDATION_SET.exists():
        raise FileNotFoundError(f"Missing validation source: {VALIDATION_SET}")

    rows: list[dict[str, Any]] = []
    for index, source in enumerate(_read_jsonl(VALIDATION_SET), start=1):
        category = str(source["category"])
        language = str(source["language"])
        frames = HINGLISH_FRAMES if language == "hinglish" else ENGLISH_FRAMES
        frame = frames[category][(index - 1) % len(frames[category])]
        query = frame.format(query=str(source["query"]).strip())
        rows.append(
            {
                **source,
                "id": f"b{index:03d}",
                "query": query,
                "split": "final_blind",
                "robustness": f"blind_{category}",
            }
        )
    return rows


def validate(rows: list[dict[str, Any]]) -> None:
    if len(rows) != 250:
        raise AssertionError(f"Expected 250 blind questions, got {len(rows)}")

    queries = [str(row["query"]).strip().lower() for row in rows]
    if len(queries) != len(set(queries)):
        raise AssertionError("Blind set contains duplicate queries")

    overlap = sorted(set(queries) & _known_queries(DEV_SET, VALIDATION_SET))
    if overlap:
        raise AssertionError(f"Blind set overlaps prior benchmarks: {overlap[:5]}")

    counts = Counter(str(row["category"]) for row in rows)
    expected = {
        "unseen_paraphrase": 100,
        "long_multi_intent": 50,
        "typo_vague": 50,
        "out_of_domain": 50,
    }
    if counts != expected:
        raise AssertionError(f"Unexpected category counts: {dict(counts)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    rows = generate()
    validate(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} frozen blind questions to {args.output}")
    for category, count in Counter(row["category"] for row in rows).items():
        print(category, count)
    print("Exact overlap with prior benchmarks: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
