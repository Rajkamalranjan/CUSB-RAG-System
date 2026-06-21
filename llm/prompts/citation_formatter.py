"""Citation formatting helpers."""

from __future__ import annotations


def format_citations(sources: list[dict]) -> str:
    lines = []
    for index, source in enumerate(sources, 1):
        title = source.get("title") or source.get("heading") or "CUSB source"
        page = f", page {source['page']}" if source.get("page") else ""
        url = f" - {source['url']}" if source.get("url") else ""
        lines.append(f"[{index}] {title}{page}{url}")
    return "\n".join(lines)

