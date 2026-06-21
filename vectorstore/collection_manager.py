"""Utilities for preparing Qdrant payloads from chunk dictionaries."""

from __future__ import annotations


def chunk_payload(chunk: dict) -> dict:
    return {
        "id": chunk.get("id"),
        "heading": chunk.get("heading"),
        "text": chunk.get("text"),
        "source_file": chunk.get("source_file"),
        "page": chunk.get("page"),
        "url": chunk.get("url"),
        "category": chunk.get("category"),
        "department": chunk.get("department"),
        "semester": chunk.get("semester"),
    }

