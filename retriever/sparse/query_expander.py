"""Lightweight query expansion for common CUSB aliases."""

from __future__ import annotations


ALIASES = {
    "hostel": "hostel mess accommodation residence",
    "fee": "fee fees structure amount payment",
    "syllabus": "syllabus course structure curriculum",
    "faculty": "faculty teacher professor department",
    "admission": "admission cuet eligibility documents",
    "exam": "exam examination result controller",
}


def expand_query(query: str) -> str:
    additions = [value for key, value in ALIASES.items() if key in query.lower()]
    return " ".join([query, *additions]).strip()

