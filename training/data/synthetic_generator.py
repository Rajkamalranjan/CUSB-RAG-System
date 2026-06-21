"""Synthetic query generation placeholder.

The actual generation should be run with an LLM provider and reviewed before
training. This module extracts candidate passages and writes a JSONL template.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path


def export_passage_templates(chunks_path: Path, output_path: Path, limit: int = 0) -> None:
    with chunks_path.open("rb") as f:
        chunks = pickle.load(f)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = chunks[:limit] if limit else chunks
    with output_path.open("w", encoding="utf-8") as out:
        for chunk in rows:
            out.write(
                json.dumps(
                    {
                        "chunk_id": chunk.get("id"),
                        "passage": chunk.get("text", ""),
                        "queries": [],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

