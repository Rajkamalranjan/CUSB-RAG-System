"""Lightweight citation and grounding checks."""

from __future__ import annotations

import re
from typing import Any


WORD_PATTERN = re.compile(r"[\w]+", flags=re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in WORD_PATTERN.findall(text or "") if len(token) > 2}


def _sentences(answer: str) -> list[str]:
    parts = re.split(r"(?<=[.!?।])\s+", answer.strip())
    return [part.strip() for part in parts if part.strip()]


def verify_answer_grounding(answer: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a conservative grounding report for generated answers.

    This is intentionally local and deterministic. It does not prove semantic
    faithfulness, but it catches many unsupported answers by checking whether
    answer sentences share meaningful tokens with retrieved context.
    """

    context = "\n".join(str(chunk.get("text", "")) for chunk in chunks)
    context_tokens = _tokens(context)
    sentences = _sentences(answer)
    if not sentences:
        return {"grounded": False, "score": 0.0, "unsupported_sentences": []}

    unsupported = []
    supported = 0
    for sentence in sentences:
        sentence_tokens = _tokens(sentence)
        if not sentence_tokens:
            supported += 1
            continue
        overlap = len(sentence_tokens & context_tokens) / max(1, len(sentence_tokens))
        if overlap >= 0.25:
            supported += 1
        else:
            unsupported.append(sentence)

    score = supported / len(sentences)
    return {
        "grounded": score >= 0.80,
        "score": round(score, 4),
        "unsupported_sentences": unsupported[:5],
    }

