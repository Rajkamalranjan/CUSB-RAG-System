"""MD5-based chunk deduplication."""

from __future__ import annotations

import hashlib


def deduplicate(chunks: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for chunk in chunks:
        digest = hashlib.md5(chunk.get("text", "").encode("utf-8", errors="ignore")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        chunk = chunk.copy()
        chunk["content_md5"] = digest
        unique.append(chunk)
    return unique

