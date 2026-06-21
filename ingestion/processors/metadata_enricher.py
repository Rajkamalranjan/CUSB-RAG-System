"""Metadata enrichment helpers."""

from __future__ import annotations

from pathlib import Path


def enrich(record: dict, category: str | None = None) -> dict:
    item = record.copy()
    source = item.get("source_file") or item.get("file") or ""
    item.setdefault("category", category or Path(source).stem if source else "unknown")
    item.setdefault("department", None)
    item.setdefault("semester", None)
    return item

