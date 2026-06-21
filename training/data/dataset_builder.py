"""Build sentence-transformers training examples from synthetic pairs."""

from __future__ import annotations

import json
from pathlib import Path


def load_pairs(path: Path) -> list[tuple[str, str]]:
    pairs = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            query = row.get("query") or row.get("question")
            positive = row.get("positive") or row.get("positive_document") or row.get("text")
            if query and positive:
                pairs.append((query, positive))
    return pairs

