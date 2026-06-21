"""Response formatting helpers."""

from __future__ import annotations

from llm.prompts.citation_formatter import format_citations


def attach_citations(answer: str, sources: list[dict]) -> str:
    citations = format_citations(sources)
    return f"{answer}\n\nSources:\n{citations}" if citations else answer

