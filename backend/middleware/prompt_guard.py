"""Backward-compatible prompt and scope guard."""

from __future__ import annotations

from backend.middleware.scope_guard import classify_scope_query


def is_safe_query(query: str) -> bool:
    return classify_scope_query(query).allowed
