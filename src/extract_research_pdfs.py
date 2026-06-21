"""Extract text from official CUSB PDF links captured in the research corpus.

The crawler preserves PDF links but does not download every PDF. This script
extracts selected PDFs into a separate source-grounded corpus so the RAG index
can include high-value syllabus, admission, fee, notice, and policy documents.

Usage examples:
    python src/extract_research_pdfs.py --limit 40
    python src/extract_research_pdfs.py --categories syllabus admission fees --limit 80
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
from PyPDF2 import PdfReader

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CORPUS = DATA_DIR / "cusb_research_corpus.jsonl"
OUTPUT_JSONL = DATA_DIR / "cusb_research_pdf_corpus.jsonl"
OUTPUT_MD = DATA_DIR / "CUSB_research_pdf_corpus.md"
OUTPUT_META = DATA_DIR / "cusb_research_pdf_corpus_meta.json"
CACHE_DIR = DATA_DIR / "pdf_cache"

USER_AGENT = "CUSB-EduRAG-ResearchBot/1.0 (+public academic PDF extraction)"
DEFAULT_KEYWORDS = (
    "syllabus",
    "course",
    "fee",
    "fees",
    "admission",
    "prospectus",
    "notification",
    "academic calendar",
    "ordinance",
    "regulation",
    "manual",
    "hostel",
)

CATEGORY_PRIORITY = {
    "fees": 0,
    "admission": 1,
    "syllabus": 2,
    "policy": 3,
    "student_support": 4,
    "faculty": 5,
    "examination": 6,
    "general": 7,
}

KEYWORD_PRIORITY = (
    "fee structure",
    "fees",
    "fee",
    "admission",
    "prospectus",
    "syllabus",
    "course structure",
    "board of studies",
    "ordinance",
    "regulation",
    "hostel",
    "academic calendar",
    "notification",
)


@dataclass
class PdfRecord:
    id: str
    title: str
    url: str
    parent_url: str
    parent_title: str
    category: str
    fetched_at_utc: str
    extracted_at_utc: str
    page_count: int
    text: str
    text_sha256: str
    char_count: int


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def pdf_id(url: str) -> str:
    return "cusb_pdf_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:14]


def pdf_cache_path(url: str) -> Path:
    return CACHE_DIR / f"{pdf_id(url)}.pdf"


def collect_pdf_links(rows: list[dict], categories: set[str], keywords: tuple[str, ...]) -> list[dict]:
    seen = set()
    links = []
    for row in rows:
        category = row.get("category", "general")
        if categories and category not in categories:
            continue
        for item in row.get("pdf_links", []):
            url = item.get("url", "")
            title = item.get("text", "").strip() or url.rsplit("/", 1)[-1]
            if not url or url in seen:
                continue
            haystack = f"{title} {url} {category}".lower()
            if keywords and not any(keyword.lower() in haystack for keyword in keywords):
                continue
            seen.add(url)
            links.append(
                {
                    "url": url,
                    "title": title,
                    "category": category,
                    "parent_url": row.get("url", ""),
                    "parent_title": row.get("title", ""),
                }
            )

    def sort_key(item: dict) -> tuple[int, int, str]:
        haystack = f"{item['title']} {item['url']}".lower()
        keyword_score = 0
        for index, keyword in enumerate(KEYWORD_PRIORITY):
            if keyword in haystack:
                keyword_score = index + 1
                break
        if keyword_score == 0:
            keyword_score = len(KEYWORD_PRIORITY) + 1
        return (
            CATEGORY_PRIORITY.get(item["category"], 99),
            keyword_score,
            item["title"].lower(),
        )

    return sorted(links, key=sort_key)


def download_pdf(session: requests.Session, url: str, timeout: int, use_cache: bool) -> bytes:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = pdf_cache_path(url)
    if use_cache and cache_path.exists():
        return cache_path.read_bytes()

    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    content = response.content
    if "pdf" not in content_type and not content[:5] == b"%PDF-":
        raise ValueError(f"Not a PDF response: content-type={content_type}")

    cache_path.write_bytes(content)
    return content


def extract_pdf_text(content: bytes, max_pages: int) -> tuple[str, int]:
    reader = PdfReader(io.BytesIO(content))
    page_count = len(reader.pages)
    extracted = []
    for index, page in enumerate(reader.pages[:max_pages], 1):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:
            page_text = f"[Page {index} extraction failed: {exc}]"
        if page_text.strip():
            extracted.append(f"--- Page {index} ---\n{page_text}")
    return normalize_text("\n\n".join(extracted)), page_count


def load_existing_records(path: Path) -> dict[str, PdfRecord]:
    if not path.exists():
        return {}
    existing = {}
    for row in load_jsonl(path):
        existing[row["url"]] = PdfRecord(**row)
    return existing


def write_outputs(records: list[PdfRecord], meta: dict) -> None:
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    md_parts = [
        "# CUSB Research PDF Corpus\n\n",
        f"Extracted at UTC: {meta['generated_at_utc']}\n\n",
        f"Records: {len(records)}\n\n",
        "---\n\n",
    ]
    for record in records:
        md_parts.append(f"## {record.title}\n\n")
        md_parts.append(f"PDF ID: {record.id}\n\n")
        md_parts.append(f"Category: {record.category}\n\n")
        md_parts.append(f"PDF URL: {record.url}\n\n")
        md_parts.append(f"Parent Source: {record.parent_url}\n\n")
        md_parts.append(f"Pages: {record.page_count}\n\n")
        md_parts.append(record.text)
        md_parts.append("\n\n---\n\n")

    OUTPUT_MD.write_text("".join(md_parts), encoding="utf-8")
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_CORPUS))
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--categories", nargs="*", default=[])
    parser.add_argument("--keywords", nargs="*", default=list(DEFAULT_KEYWORDS))
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--max-pages-per-pdf", type=int, default=25)
    parser.add_argument("--min-chars", type=int, default=300)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    selected = collect_pdf_links(rows, set(args.categories), tuple(args.keywords))
    if args.limit:
        selected = selected[: args.limit]

    existing = load_existing_records(OUTPUT_JSONL) if args.resume else {}
    records = list(existing.values())
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    stats = {
        "selected": len(selected),
        "attempted": 0,
        "extracted": 0,
        "skipped_existing": 0,
        "skipped_short": 0,
        "failed": 0,
        "errors": [],
    }

    for index, item in enumerate(selected, 1):
        url = item["url"]
        if url in existing:
            stats["skipped_existing"] += 1
            continue

        print(f"[{index:03d}/{len(selected)}] {item['title'][:90]}")
        print(f"  {url}")
        stats["attempted"] += 1
        try:
            content = download_pdf(session, url, args.timeout, use_cache=not args.no_cache)
            text, page_count = extract_pdf_text(content, max_pages=args.max_pages_per_pdf)
            if len(text) < args.min_chars:
                print(f"  skipped: only {len(text)} chars")
                stats["skipped_short"] += 1
                time.sleep(args.delay)
                continue

            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            record = PdfRecord(
                id=pdf_id(url),
                title=item["title"],
                url=url,
                parent_url=item["parent_url"],
                parent_title=item["parent_title"],
                category=item["category"],
                fetched_at_utc=datetime.now(timezone.utc).isoformat(),
                extracted_at_utc=datetime.now(timezone.utc).isoformat(),
                page_count=page_count,
                text=text,
                text_sha256=text_hash,
                char_count=len(text),
            )
            records.append(record)
            existing[url] = record
            stats["extracted"] += 1
            print(f"  ok: {len(text):,} chars, {page_count} pages")
        except Exception as exc:
            stats["failed"] += 1
            message = f"{url}: {exc}"
            stats["errors"].append(message)
            print(f"  failed: {exc}")

        time.sleep(args.delay)

    meta = {
        **stats,
        "input": str(args.input),
        "output_jsonl": str(OUTPUT_JSONL),
        "output_markdown": str(OUTPUT_MD),
        "cache_dir": str(CACHE_DIR),
        "categories": args.categories,
        "keywords": args.keywords,
        "limit": args.limit,
        "max_pages_per_pdf": args.max_pages_per_pdf,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_outputs(records, meta)

    print("\nPDF extraction complete")
    print(f"  Total records: {len(records)}")
    print(f"  Extracted now: {stats['extracted']}")
    print(f"  Failed       : {stats['failed']}")
    print(f"  JSONL        : {OUTPUT_JSONL}")
    print(f"  Markdown     : {OUTPUT_MD}")
    print(f"  Metadata     : {OUTPUT_META}")


if __name__ == "__main__":
    main()
