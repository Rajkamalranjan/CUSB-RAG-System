"""Generate synthetic query-positive pairs from existing chunks.

Uses Gemini when GEMINI_API_KEY is available. Without a key, it creates a
review template so the pipeline remains runnable.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in text.split() if len(token) > 2]


PROMPT = """Generate 3 student-style Hindi/English/Hinglish questions answered by this CUSB passage.
Return only JSON list of strings.

Passage:
{passage}
"""


def gemini_questions(passage: str) -> list[str]:
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))
    response = model.generate_content(PROMPT.format(passage=passage[:2500]))
    text = getattr(response, "text", "[]")
    try:
        data = json.loads(text[text.find("[") : text.rfind("]") + 1])
        return [str(item) for item in data][:5]
    except Exception:
        return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", default="data/cusb_chunks.pkl")
    parser.add_argument("--output", default="data/benchmark/synthetic_pairs.jsonl")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    with Path(args.chunks).open("rb") as f:
        chunks = pickle.load(f)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    corpus_tokens = [tokenize(f"{chunk.get('heading', '')} {chunk.get('text', '')}") for chunk in chunks]
    bm25 = BM25Okapi(corpus_tokens)

    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    with output.open("w", encoding="utf-8") as out:
        for chunk in chunks[: args.limit]:
            passage = chunk.get("text", "")
            if not passage.strip():
                continue
            questions = gemini_questions(passage) if has_gemini else []
            if not questions:
                title = chunk.get("heading") or "this CUSB information"
                questions = [f"What does CUSB say about {title}?"]
            for question in questions:
                negative_ids = []
                scores = bm25.get_scores(tokenize(question))
                ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
                for index, _score in ranked:
                    candidate = chunks[index]
                    if candidate.get("id") == chunk.get("id"):
                        continue
                    negative_ids.append(candidate.get("id"))
                    if len(negative_ids) >= 5:
                        break
                out.write(
                    json.dumps(
                        {
                            "query": question,
                            "positive": passage,
                            "chunk_id": chunk.get("id"),
                            "source_file": chunk.get("source_file"),
                            "hard_negative_chunk_ids": negative_ids,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
