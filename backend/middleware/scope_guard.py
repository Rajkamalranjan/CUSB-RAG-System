"""Deterministic scope and safety guard for the CUSB student assistant."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeDecision:
    allowed: bool
    reason: str = "allowed"


HINGLISH_MARKERS = (
    "aaj", "abhi", "batao", "btao", "chahiye", "hai", "hain", "ka", "kaise",
    "kal", "kara", "karao", "kare", "karke", "karo", "ke", "kha", "ki", "kis",
    "kya", "liye", "mein", "mera", "mere", "milegi", "milta", "par", "se",
)


PROMPT_INJECTION_PATTERNS = (
    r"\bignore\s+(?:all\s+|the\s+)?(?:previous\s+)?(?:rules|instructions)\b",
    r"\b(?:reveal|show|share|display|print)\b.{0,40}\b(?:system|developer|hidden)\s+(?:prompt|message|instructions?)\b",
    r"\b(?:system|developer)\s+(?:prompt|message)\b",
    r"\bsystem\s+instructions?\b",
)

SENSITIVE_DATA_PATTERNS = (
    r"\b(?:admin|portal|student|cusb)\b.{0,30}\b(?:password|secret|credentials?|api\s*key)\b",
    r"\b(?:password|secret|credentials?|api\s*key)\b.{0,30}\b(?:batao|do|reveal|share|dikhao|show|give)\b",
    r"\b(?:private|personal|confidential|internal)\b.{0,45}\b(?:email|files?|docs?|documents?|phone|mobile|number|records?|list)\b",
    r"\b(?:student|faculty|applicant)\b.{0,30}\b(?:private|personal)\b.{0,25}\b(?:phone|mobile|number|email|records?)\b",
)

PRIVILEGED_ACTION_PATTERNS = (
    r"\b(?:delete|remove|erase)\b.{0,35}\b(?:all\s+)?(?:data|database|records?|files?)\b",
    r"\b(?:data|database|records?|files?)\b.{0,35}\b(?:delete|remove|erase)\b",
    r"\b(?:bypass|skip|break)\b.{0,25}\b(?:login|password|portal|authentication)\b",
    r"\b(?:login|password|portal|authentication)\b.{0,25}\b(?:bypass|skip|break|karao)\b",
    r"\b(?:change|edit|increase|modify)\b.{0,30}\b(?:marks?|grades?|result)\b",
    r"\b(?:marks?|grades?|result)\b.{0,30}\b(?:change|edit|increase|modify|karao)\b",
    r"\b(?:book|reserve|allot)\b.{0,35}\b(?:hostel|room|seat)\b.{0,20}\b(?:for\s+me|my\s+name|mere|mera|naam)\b",
    r"\b(?:mere|mera|my)\b.{0,30}\b(?:hostel|room|seat)\b.{0,20}\b(?:book|reserve|allot)\b",
    r"\b(?:send|bhejo)\b.{0,30}\b(?:email|message)\b.{0,30}\b(?:from\s+my|mere\s+account)\b",
    r"\b(?:my|mere)\s+account\b.{0,35}\b(?:email|message)\b.{0,15}\b(?:send|bhejo)\b",
    r"\b(?:guarantee|confirm)\b.{0,25}\b(?:admission|selection)\b.{0,30}\b(?:without|bina)\b",
    r"\b(?:without|bina)\b.{0,30}\b(?:admission|selection)\b.{0,20}\b(?:guarantee|confirm|de\s+do)\b",
    r"\b(?:direct\s+admission|admission\s+de\s+do|fee\s+free\s+kar)\b",
)

OUT_OF_DOMAIN_PATTERNS = (
    r"\b(?:weather|temperature|forecast)\b",
    r"\b(?:stock|bitcoin|crypto|share\s+market)\b",
    r"\b(?:ipl|cricket|football)\b.{0,35}\b(?:score|match|final|won|jeeta|winner)\b",
    r"\b(?:generate|write|bana|banao)\b.{0,30}\b(?:java|python|javascript|c\+\+|calculator|sorting)\b.{0,20}\bcode\b",
    r"\b(?:java|python|javascript|c\+\+)\b.{0,20}\bcode\b",
    r"\b(?:movie|film)\b.{0,20}\b(?:story|script)\b",
    r"\b(?:political|campaign)\b.{0,25}\bspeech\b",
    r"\b(?:medical|medicine|fever)\b.{0,30}\b(?:prescription|prescribe|diagnosis|diagnose)\b",
    r"\b(?:legal|court)\b.{0,30}\b(?:advice|dispute|case)\b",
    r"\brailway\s+ticket\b.{0,30}\b(?:availability|booking|book)\b",
)

TIME_SENSITIVE_PATTERNS = (
    r"\b(?:today|aaj|tomorrow|kal|right\s+now|abhi|current|exact)\b.{0,45}\b(?:canteen|mess)\b.{0,20}\bmenu\b",
    r"\b(?:today|aaj|tomorrow|kal|right\s+now|abhi|current|exact)\b.{0,45}\b(?:topper|exam\s+room|hostel\s+room\s+availability)\b",
    r"\b(?:canteen|mess)\b.{0,20}\bmenu\b.{0,25}\b(?:today|aaj|tomorrow|kal|right\s+now|abhi|current|exact)\b",
    r"\b(?:topper|exam\s+room|hostel\s+room\s+availability)\b.{0,35}\b(?:today|aaj|tomorrow|kal|right\s+now|abhi|current|exact)\b",
    r"\b(?:20[3-9]\d)\b.{0,35}\b(?:admission|exam|counselling)\b.{0,15}\b(?:date|deadline|schedule)\b",
)


def _normalize(query: str) -> str:
    return re.sub(r"\s+", " ", query.lower()).strip()


def _matches(query: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, query, flags=re.IGNORECASE) for pattern in patterns)


def classify_scope_query(query: str) -> ScopeDecision:
    """Classify queries that should not reach retrieval or generation."""

    normalized = _normalize(query)
    if _matches(normalized, PROMPT_INJECTION_PATTERNS):
        return ScopeDecision(False, "prompt_injection")
    if _matches(normalized, PRIVILEGED_ACTION_PATTERNS):
        return ScopeDecision(False, "privileged_action")
    if _matches(normalized, SENSITIVE_DATA_PATTERNS):
        return ScopeDecision(False, "sensitive_data")
    if _matches(normalized, TIME_SENSITIVE_PATTERNS):
        return ScopeDecision(False, "time_sensitive")
    if _matches(normalized, OUT_OF_DOMAIN_PATTERNS):
        return ScopeDecision(False, "out_of_domain")
    return ScopeDecision(True)


def looks_hinglish(query: str) -> bool:
    normalized = _normalize(query)
    return any(re.search(rf"\b{re.escape(marker)}\b", normalized) for marker in HINGLISH_MARKERS)


def scope_refusal_answer(query: str) -> str:
    if looks_hinglish(query):
        return (
            "Available CUSB data me yeh information nahi mili. Main sirf verified CUSB-related "
            "admission, courses, faculty, fees, facilities aur examination information me help kar sakta hoon."
        )
    return (
        "I could not find this in available CUSB data. I can only help with verified CUSB-related "
        "admissions, courses, faculty, fees, facilities, and examination information."
    )
