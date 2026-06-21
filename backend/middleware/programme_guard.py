"""Evidence-based guard for unsupported CUSB programme availability claims."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "cusb_chunks_clean.jsonl"
_AVAILABILITY_PATTERNS = (
    re.compile(r"\b(?:does|do)\s+cusb\s+(?:offer|operate|run|provide)\b"),
    re.compile(r"\bis\s+.+\b(?:available|offered)\s+(?:at|in|by)\s+cusb\b"),
    re.compile(r"\bcusb\b.+\b(?:offer|offers|offered|chalata|chalati)\b"),
    re.compile(r"\bcusb\b.+\b(?:course|programme|program)\s+hai\s+kya\b"),
)
_QUERY_NOISE = {
    "a", "an", "at", "by", "cusb", "does", "do", "in", "is", "of", "the",
    "available", "availability", "course", "courses", "medical", "college",
    "offer", "offered", "offering", "offers", "operate", "operates", "provide",
    "program", "programme", "programs", "programmes", "run", "runs",
    "chalata", "chalati", "hai", "karta", "karti", "ka", "ki", "kya", "me",
}


@dataclass(frozen=True)
class ProgrammeDecision:
    applicable: bool
    supported: bool
    candidate: str = ""


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _tokenize(text: str) -> set[str]:
    aliases = {
        "ba": ("b", "a"),
        "llb": ("l", "l", "b"),
        "ma": ("m", "a"),
        "msc": ("m", "sc"),
    }
    tokens: set[str] = set()
    for token in _normalize(text).split():
        tokens.update(aliases.get(token, (token,)))
    return tokens


@lru_cache(maxsize=1)
def _official_programme_text() -> str:
    """Load only official department-programme chunks, excluding incidental mentions."""
    records: list[str] = []
    try:
        with _DATA_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("section") == "Department & Programmes":
                    records.append(str(record.get("text", "")))
    except (OSError, json.JSONDecodeError):
        return ""
    return "\n".join(records)


def _candidate_from_query(query: str) -> str:
    normalized = _normalize(query)
    # Prefer content after "offering" or "offer": it is usually the requested degree.
    for marker in (" offering ", " offer ", " offers ", " offered "):
        if marker in f" {normalized} ":
            before, after = normalized.rsplit(marker.strip(), maxsplit=1)
            after_tokens = [token for token in after.split() if token not in _QUERY_NOISE]
            normalized = after if after_tokens else before
            break
    tokens = [token for token in normalized.split() if token not in _QUERY_NOISE]
    return " ".join(tokens)


def classify_programme_query(query: str) -> ProgrammeDecision:
    normalized = _normalize(query)
    if not any(pattern.search(normalized) for pattern in _AVAILABILITY_PATTERNS):
        return ProgrammeDecision(applicable=False, supported=True)

    candidate = _candidate_from_query(query)
    if not candidate:
        return ProgrammeDecision(applicable=False, supported=True)

    official_tokens = _tokenize(_official_programme_text())
    candidate_tokens = _tokenize(candidate)
    supported = bool(official_tokens and candidate_tokens and candidate_tokens <= official_tokens)
    return ProgrammeDecision(applicable=True, supported=supported, candidate=candidate)


def unsupported_programme_answer(query: str) -> str:
    from backend.middleware.scope_guard import looks_hinglish

    if looks_hinglish(query):
        return (
            "Available official CUSB programme data me yeh course verify nahi hua. "
            "Current availability ke liye latest CUSB admission bulletin check karein."
        )
    return (
        "I could not verify this programme in the available official CUSB programme data. "
        "Please check the latest CUSB admission bulletin for current availability."
    )
