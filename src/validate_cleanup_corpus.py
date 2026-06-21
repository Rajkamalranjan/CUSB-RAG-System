"""Validate and safely clean extracted CUSB JSONL corpora.

This pass is intentionally conservative:
- fixes mojibake, spacing, line-break, and OCR junk artifacts
- does not rewrite official names, dates, amounts, URLs, or course codes
- flags suspicious OCR text for manual review instead of guessing

Usage:
    python src/validate_cleanup_corpus.py \
        --input data/cusb_about_university_pdfs.jsonl \
        --output-jsonl data/cusb_about_university_pdfs_clean.jsonl \
        --output-md data/CUSB_about_university_pdfs_clean.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MOJIBAKE_MAP = {
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€": '"',
    "â€“": "-",
    "â€”": "-",
    "â€¢": "-",
    "Â ": " ",
    "Â": "",
    "ï¬": "fi",
    "ï¬‚": "fl",
}

DOMAIN_TERMS = [
    "Central University of South Bihar",
    "CUSB",
    "Panchanpur",
    "Aryabhatta Bhawan",
    "Chanakya Bhawan",
    "Malaviya Bhawan",
    "Vivekanand Lecture Complex",
    "Sangharam Guest House",
    "Gargi Sadan",
    "Maitreyi Sadan",
]

OFFICIAL_TOKEN_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|[A-Z]{2,}[-/]?\d+[A-Z0-9/-]*|\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|₹\s?\d[\d,]*|\b\d+/\d+\b)"
)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def repair_mojibake(text: str) -> str:
    for bad, good in MOJIBAKE_MAP.items():
        text = text.replace(bad, good)
    if re.search(r"[âÃ€œ€€™“”]", text):
        try:
            repaired = text.encode("cp1252", errors="ignore").decode("utf-8", errors="ignore")
            if repaired and repaired.count("�") <= text.count("�"):
                text = repaired
        except Exception:
            pass
    return text


def protect_official_tokens(text: str) -> tuple[str, dict[str, str]]:
    protected = {}

    def replace(match: re.Match) -> str:
        key = f"__CUSB_PROTECTED_{len(protected)}__"
        protected[key] = match.group(0)
        return key

    for term in DOMAIN_TERMS:
        if term in text:
            key = f"__CUSB_PROTECTED_{len(protected)}__"
            protected[key] = term
            text = text.replace(term, key)
    text = OFFICIAL_TOKEN_PATTERN.sub(replace, text)
    return text, protected


def restore_official_tokens(text: str, protected: dict[str, str]) -> str:
    for key, value in protected.items():
        text = text.replace(key, value)
    return text


def safe_cleanup_text(text: str) -> str:
    text = repair_mojibake(text)
    text, protected = protect_official_tokens(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[|]{3,}", " | ", text)
    text = re.sub(r"[_]{4,}", " ___ ", text)
    text = re.sub(r"([A-Za-z])\s+([,.])", r"\1\2", text)
    text = re.sub(r"\s+([:;!?])", r"\1", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = restore_official_tokens(text, protected)
    return text.strip()


def suspicious_signals(text: str) -> list[str]:
    signals = []
    plain = re.sub(r"\s+", "", text)
    if not text.strip():
        signals.append("empty_text")
        return signals
    chars = [char for char in text if not char.isspace()]
    if chars:
        junk = sum(char in "|\\/_=<>[]{}~^`" for char in chars) / len(chars)
        alpha = sum(char.isalpha() for char in chars) / len(chars)
        if junk > 0.12:
            signals.append("high_junk_character_ratio")
        if alpha < 0.35 and len(chars) > 80:
            signals.append("low_alpha_ratio")
    if re.search(r"\b[A-Za-z]{1}\s+[A-Za-z]{1}\s+[A-Za-z]{1}\s+[A-Za-z]{1}\b", text):
        signals.append("spaced_letters")
    if len(re.findall(r"\b\w{18,}\b", text)) >= 5:
        signals.append("many_unusually_long_tokens")
    if len(plain) > 100 and len(set(plain)) < 12:
        signals.append("repetitive_low_variety_text")
    return signals


def page_quality_report(text: str) -> list[dict]:
    reports = []
    page_pattern = re.compile(r"--- Page (\d+) \[([^\]]+)\] ---\n(.*?)(?=\n--- Page \d+ \[|\Z)", re.DOTALL)
    for match in page_pattern.finditer(text):
        page_no = int(match.group(1))
        method = match.group(2)
        page_text = match.group(3).strip()
        signals = suspicious_signals(page_text)
        if signals:
            reports.append({"page": page_no, "method": method, "signals": signals})
    if not reports and suspicious_signals(text):
        reports.append({"page": None, "method": "unknown", "signals": suspicious_signals(text)})
    return reports


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_markdown(path: Path, rows: list[dict], meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        "# CUSB Cleaned Corpus\n\n",
        f"Cleaned at UTC: {meta['cleaned_at_utc']}\n\n",
        f"Records: {meta['records']}\n\n",
        f"Records flagged for review: {meta['flagged_records']}\n\n",
        "---\n\n",
    ]
    for row in rows:
        title = row.get("title") or row.get("heading") or row.get("id") or "CUSB Record"
        parts.append(f"## {title}\n\n")
        if row.get("section"):
            parts.append(f"**Section:** {row['section']}\n\n")
        if row.get("url"):
            parts.append(f"**URL:** {row['url']}\n\n")
        if row.get("source_file"):
            parts.append(f"**Source File:** {row['source_file']}\n\n")
        if row.get("validation_flags"):
            parts.append(f"**Validation Flags:** `{', '.join(row['validation_flags'])}`\n\n")
        if row.get("page_quality_issues"):
            parts.append("**Pages Needing Review:**\n\n")
            for issue in row["page_quality_issues"][:20]:
                parts.append(f"- Page {issue.get('page')}: {', '.join(issue.get('signals', []))}\n")
            parts.append("\n")
        parts.append("```text\n")
        parts.append(row.get("text", ""))
        parts.append("\n```\n\n---\n\n")
    path.write_text("".join(parts), encoding="utf-8")


def clean_rows(rows: list[dict]) -> tuple[list[dict], dict]:
    cleaned = []
    flagged = 0
    page_issue_count = 0
    for row in rows:
        item = row.copy()
        original = item.get("text", "")
        text = safe_cleanup_text(original)
        issues = page_quality_report(text)
        flags = []
        if repair_mojibake(original) != original:
            flags.append("mojibake_repaired")
        if issues:
            flags.append("review_needed")
            flagged += 1
            page_issue_count += len(issues)
        item["text"] = text
        item["char_count"] = len(text)
        item["text_sha256"] = text_hash(text)
        item["validation_flags"] = flags
        item["page_quality_issues"] = issues
        cleaned.append(item)
    meta = {
        "cleaned_at_utc": datetime.now(timezone.utc).isoformat(),
        "records": len(cleaned),
        "flagged_records": flagged,
        "page_quality_issue_count": page_issue_count,
        "policy": "safe cleanup only; official tokens preserved; suspicious OCR flagged",
    }
    return cleaned, meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-meta", default="")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    cleaned, meta = clean_rows(rows)
    write_jsonl(Path(args.output_jsonl), cleaned)
    write_markdown(Path(args.output_md), cleaned, meta)
    meta_path = Path(args.output_meta) if args.output_meta else Path(args.output_jsonl).with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

