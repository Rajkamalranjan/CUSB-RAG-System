"""Build a clean, source-grounded corpus from raw CUSB scrape output.

Input:
    data/cusb_research_scrape.jsonl

Outputs:
    data/cusb_research_corpus.jsonl
    data/CUSB_research_corpus.md
    data/cusb_research_corpus_meta.json

The raw crawler intentionally preserves page text and links. This builder turns
that audit trail into RAG-ready records by removing repeated navigation lines,
deduplicating pages, keeping PDF links, and attaching source metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_INPUT = DATA_DIR / "cusb_research_scrape.jsonl"
OUTPUT_JSONL = DATA_DIR / "cusb_research_corpus.jsonl"
OUTPUT_MD = DATA_DIR / "CUSB_research_corpus.md"
OUTPUT_META = DATA_DIR / "cusb_research_corpus_meta.json"


STATIC_NOISE = {
    "home",
    "about",
    "academics",
    "administration",
    "admission",
    "research",
    "student corner",
    "webmail",
    "download",
    "notices",
    "upcoming events",
    "archived events",
    "photo gallery",
    "recruitment",
    "feedback:",
    "[ rti ]",
    "[ public self disclosure ]",
    "important links",
    "follow us",
    "locate us",
}

SECTION_KEYWORDS = {
    "admission": {"admission", "cuet", "application", "notification", "prospectus"},
    "syllabus": {"syllabus", "course structure", "curriculum", "programme", "program"},
    "examination": {"examination", "exam", "result", "notice"},
    "fees": {"fee", "fees", "payment", "hostel", "mess"},
    "faculty": {"faculty", "professor", "department", "school", "dean", "head"},
    "policy": {"ordinance", "regulation", "policy", "statute", "manual"},
    "student_support": {"student", "welfare", "hostel", "scholarship", "anti-ragging"},
}


@dataclass
class CorpusRecord:
    id: str
    title: str
    url: str
    category: str
    fetched_at_utc: str
    built_at_utc: str
    text: str
    text_sha256: str
    char_count: int
    pdf_links: list[dict]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line).strip()
    line = line.strip("|•*-")
    return line.strip()


def page_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        cleaned = normalize_line(line)
        if cleaned:
            lines.append(cleaned)
    return lines


def high_frequency_noise(rows: list[dict], min_ratio: float) -> set[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        unique_lines = {line.lower() for line in page_lines(row.get("text", ""))}
        counter.update(unique_lines)

    threshold = max(2, int(len(rows) * min_ratio))
    return {line for line, count in counter.items() if count >= threshold}


def looks_like_noise(line: str, repeated_lines: set[str]) -> bool:
    lower = line.lower()
    if lower in STATIC_NOISE or lower in repeated_lines:
        return True
    if len(line) <= 2:
        return True
    if re.fullmatch(r"[.\-_= ]{5,}", line):
        return True
    if re.fullmatch(r"\d{3,}[-\d ]+", line):
        return True
    if lower.startswith("central university of south bihar") and len(line) < 80:
        return True
    return False


def clean_page_text(text: str, repeated_lines: set[str], min_line_chars: int) -> str:
    cleaned_lines = []
    previous = None
    for line in page_lines(text):
        if len(line) < min_line_chars and not re.search(r"\d", line):
            continue
        if looks_like_noise(line, repeated_lines):
            continue
        if line == previous:
            continue
        cleaned_lines.append(line)
        previous = line

    # Preserve readable paragraphs while keeping page order.
    return "\n".join(cleaned_lines).strip()


def categorize(title: str, url: str, text: str) -> str:
    haystack = f"{title} {url} {text[:2000]}".lower()
    scores = {
        category: sum(1 for keyword in keywords if keyword in haystack)
        for category, keywords in SECTION_KEYWORDS.items()
    }
    best_category, best_score = max(scores.items(), key=lambda item: item[1])
    return best_category if best_score else "general"


def stable_page_id(url: str, text: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    article_id = query.get("id", [""])[0]
    item_id = query.get("Itemid", [""])[0]
    basis = f"{parsed.path}|{article_id}|{item_id}|{hashlib.sha1(text[:500].encode('utf-8')).hexdigest()[:10]}"
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
    return f"cusb_page_{digest}"


def dedupe_pdf_links(items: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for item in items:
        url = item.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        output.append({"text": item.get("text", "").strip(), "url": url})
    return output


def build_corpus(rows: list[dict], min_chars: int, min_line_chars: int, noise_ratio: float) -> tuple[list[CorpusRecord], dict]:
    repeated_lines = high_frequency_noise(rows, noise_ratio)
    seen_hashes = set()
    seen_clean_hashes = set()
    records: list[CorpusRecord] = []
    skipped = Counter()
    built_at = datetime.now(timezone.utc).isoformat()

    for row in rows:
        original_hash = row.get("text_sha256") or hashlib.sha256(row.get("text", "").encode("utf-8")).hexdigest()
        if original_hash in seen_hashes:
            skipped["duplicate_raw_hash"] += 1
            continue
        seen_hashes.add(original_hash)

        text = clean_page_text(row.get("text", ""), repeated_lines, min_line_chars)
        if len(text) < min_chars:
            skipped["too_short_after_cleaning"] += 1
            continue

        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text_hash in seen_clean_hashes:
            skipped["duplicate_clean_hash"] += 1
            continue
        seen_clean_hashes.add(text_hash)

        record = CorpusRecord(
            id=stable_page_id(row.get("url", ""), text),
            title=row.get("title", "").replace(" - Central University of South Bihar, Gaya, Bihar", "").strip(),
            url=row.get("url", ""),
            category=categorize(row.get("title", ""), row.get("url", ""), text),
            fetched_at_utc=row.get("fetched_at_utc", ""),
            built_at_utc=built_at,
            text=text,
            text_sha256=text_hash,
            char_count=len(text),
            pdf_links=dedupe_pdf_links(row.get("pdf_links", [])),
        )
        records.append(record)

    meta = {
        "input_pages": len(rows),
        "output_records": len(records),
        "skipped": dict(skipped),
        "noise_line_count": len(repeated_lines),
        "min_chars": min_chars,
        "min_line_chars": min_line_chars,
        "noise_ratio": noise_ratio,
        "built_at_utc": built_at,
        "category_counts": dict(Counter(record.category for record in records)),
        "total_chars": sum(record.char_count for record in records),
        "total_pdf_links": sum(len(record.pdf_links) for record in records),
    }
    return records, meta


def save_outputs(records: list[CorpusRecord], meta: dict) -> None:
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    md_parts = [
        "# CUSB Research Corpus\n\n",
        f"Built at UTC: {meta['built_at_utc']}\n\n",
        f"Records: {meta['output_records']}\n\n",
        f"Total characters: {meta['total_chars']}\n\n",
        "---\n\n",
    ]
    for record in records:
        md_parts.append(f"## {record.title}\n\n")
        md_parts.append(f"Record ID: {record.id}\n\n")
        md_parts.append(f"Category: {record.category}\n\n")
        md_parts.append(f"Source: {record.url}\n\n")
        if record.pdf_links:
            md_parts.append("PDF Links:\n")
            for item in record.pdf_links:
                label = item["text"] or item["url"]
                md_parts.append(f"- [{label}]({item['url']})\n")
            md_parts.append("\n")
        md_parts.append(record.text)
        md_parts.append("\n\n---\n\n")

    OUTPUT_MD.write_text("".join(md_parts), encoding="utf-8")
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--min-chars", type=int, default=500)
    parser.add_argument("--min-line-chars", type=int, default=4)
    parser.add_argument("--noise-ratio", type=float, default=0.35)
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    records, meta = build_corpus(
        rows,
        min_chars=args.min_chars,
        min_line_chars=args.min_line_chars,
        noise_ratio=args.noise_ratio,
    )
    save_outputs(records, meta)

    print("Research corpus built")
    print(f"  Input pages : {meta['input_pages']}")
    print(f"  Records     : {meta['output_records']}")
    print(f"  Chars       : {meta['total_chars']:,}")
    print(f"  PDF links   : {meta['total_pdf_links']}")
    print(f"  Categories  : {meta['category_counts']}")
    print(f"  JSONL       : {OUTPUT_JSONL}")
    print(f"  Markdown    : {OUTPUT_MD}")
    print(f"  Metadata    : {OUTPUT_META}")


if __name__ == "__main__":
    main()
