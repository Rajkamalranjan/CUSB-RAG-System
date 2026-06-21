"""Research-grade polite crawler for public CUSB website data.

The goal is auditability for RAG research: every extracted page keeps its source
URL, title, discovered links, PDF links, and cleaned text. The crawler stays on
cusb.ac.in, respects common robots.txt disallow paths, uses a delay between
requests, and avoids private/admin/API paths.

Usage:
    python src/scrape_cusb_research.py --max-pages 60
    python src/scrape_cusb_research.py --seed https://www.cusb.ac.in/index.php --max-pages 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BASE_URL = "https://www.cusb.ac.in"
BASE_DOMAIN = "www.cusb.ac.in"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_JSONL = DATA_DIR / "cusb_research_scrape.jsonl"
OUTPUT_MD = DATA_DIR / "CUSB_research_scrape.md"
OUTPUT_META = DATA_DIR / "cusb_research_scrape_meta.json"

USER_AGENT = "CUSB-EduRAG-ResearchBot/1.0 (+public academic data collection)"
ROBOTS_DISALLOW = (
    "/administrator/",
    "/api/",
    "/bin/",
    "/cache/",
    "/cli/",
    "/components/",
    "/includes/",
    "/installation/",
    "/language/",
    "/layouts/",
    "/libraries/",
    "/logs/",
    "/modules/",
    "/plugins/",
    "/tmp/",
)

IMPORTANT_KEYWORDS = {
    "admission",
    "fee",
    "fees",
    "syllabus",
    "course",
    "programme",
    "program",
    "faculty",
    "department",
    "school",
    "student",
    "hostel",
    "notice",
    "academic",
    "exam",
    "cuet",
    "iqac",
    "naac",
    "ordinance",
    "regulation",
    "prospectus",
}


@dataclass
class ScrapedPage:
    url: str
    title: str
    fetched_at_utc: str
    status_code: int
    content_type: str
    text: str
    text_sha256: str
    links: list[dict]
    pdf_links: list[dict]


def normalize_url(url: str, base_url: str = BASE_URL) -> str | None:
    absolute = urljoin(base_url, url)
    absolute, _fragment = urldefrag(absolute)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc.lower() not in {BASE_DOMAIN, "cusb.ac.in"}:
        return None
    return absolute


def is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if any(path.startswith(disallowed) for disallowed in ROBOTS_DISALLOW):
        return False
    if re.search(r"\.(jpg|jpeg|png|gif|svg|css|js|zip|rar|doc|docx|xls|xlsx)$", path, re.I):
        return False
    return True


def relevance_score(url: str, text: str) -> int:
    haystack = f"{url} {text}".lower()
    return sum(1 for keyword in IMPORTANT_KEYWORDS if keyword in haystack)


def clean_text(soup: BeautifulSoup) -> str:
    for element in soup(["script", "style", "noscript", "form"]):
        element.decompose()

    main = None
    for selector in (
        "main",
        "article",
        ".item-page",
        ".content",
        "#content",
        ".entry-content",
        "[role='main']",
    ):
        main = soup.select_one(selector)
        if main:
            break

    if main is None:
        main = soup.body or soup

    text = main.get_text(separator="\n", strip=True)
    lines = []
    seen = set()
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if len(cleaned) < 3:
            continue
        lower = cleaned.lower()
        if lower in seen:
            continue
        seen.add(lower)
        lines.append(cleaned)

    return "\n".join(lines)


def extract_links(soup: BeautifulSoup, page_url: str) -> tuple[list[dict], list[dict]]:
    links = []
    pdf_links = []

    for a_tag in soup.find_all("a", href=True):
        text = re.sub(r"\s+", " ", a_tag.get_text(" ", strip=True)).strip()
        normalized = normalize_url(a_tag["href"], page_url)
        if not normalized or not is_allowed(normalized):
            continue

        item = {"text": text, "url": normalized}
        if normalized.lower().endswith(".pdf") or "pdf" in normalized.lower():
            pdf_links.append(item)
        else:
            links.append(item)

    return dedupe_links(links), dedupe_links(pdf_links)


def dedupe_links(items: Iterable[dict]) -> list[dict]:
    seen = set()
    output = []
    for item in items:
        key = item["url"]
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def fetch_page(session: requests.Session, url: str, timeout: int) -> ScrapedPage | None:
    response = session.get(url, timeout=timeout)
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type.lower():
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = clean_text(soup)
    links, pdf_links = extract_links(soup, url)

    return ScrapedPage(
        url=url,
        title=title or url,
        fetched_at_utc=datetime.now(timezone.utc).isoformat(),
        status_code=response.status_code,
        content_type=content_type,
        text=text,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        links=links,
        pdf_links=pdf_links,
    )


def crawl(seed_url: str, max_pages: int, delay: float, timeout: int) -> list[ScrapedPage]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    queue = deque([seed_url])
    queued = {seed_url}
    visited = set()
    pages: list[ScrapedPage] = []

    while queue and len(pages) < max_pages:
        url = queue.popleft()
        queued.discard(url)
        if url in visited or not is_allowed(url):
            continue
        visited.add(url)

        print(f"[{len(pages) + 1:03d}/{max_pages}] {url}")
        try:
            page = fetch_page(session, url, timeout)
        except requests.RequestException as exc:
            print(f"  skipped: {exc}")
            time.sleep(delay)
            continue

        if page and len(page.text) >= 100:
            pages.append(page)
            candidates = sorted(
                page.links,
                key=lambda item: relevance_score(item["url"], item.get("text", "")),
                reverse=True,
            )
            for item in candidates:
                next_url = item["url"]
                if next_url not in visited and next_url not in queued and is_allowed(next_url):
                    queue.append(next_url)
                    queued.add(next_url)

            print(f"  ok: {len(page.text):,} chars, {len(page.links)} links, {len(page.pdf_links)} pdfs")
        else:
            print("  skipped: no useful HTML text")

        time.sleep(delay)

    return pages


def save_outputs(pages: list[ScrapedPage], seed_url: str, max_pages: int, delay: float) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for page in pages:
            f.write(json.dumps(asdict(page), ensure_ascii=False) + "\n")

    md_parts = [
        "# CUSB Research Scrape\n\n",
        f"Scraped at UTC: {datetime.now(timezone.utc).isoformat()}\n\n",
        f"Seed URL: {seed_url}\n\n",
        f"Pages: {len(pages)}\n\n",
        "---\n\n",
    ]
    for page in pages:
        md_parts.append(f"## {page.title}\n\n")
        md_parts.append(f"Source: {page.url}\n\n")
        if page.pdf_links:
            md_parts.append("PDF Links:\n")
            for item in page.pdf_links:
                label = item["text"] or item["url"]
                md_parts.append(f"- [{label}]({item['url']})\n")
            md_parts.append("\n")
        md_parts.append(page.text)
        md_parts.append("\n\n---\n\n")

    OUTPUT_MD.write_text("".join(md_parts), encoding="utf-8")

    meta = {
        "seed_url": seed_url,
        "max_pages": max_pages,
        "delay_seconds": delay,
        "pages_saved": len(pages),
        "jsonl": str(OUTPUT_JSONL),
        "markdown": str(OUTPUT_MD),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "robots_disallow_respected": list(ROBOTS_DISALLOW),
        "user_agent": USER_AGENT,
    }
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=BASE_URL)
    parser.add_argument("--max-pages", type=int, default=60)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    seed = normalize_url(args.seed)
    if not seed:
        raise ValueError(f"Seed URL is outside allowed CUSB domain: {args.seed}")

    pages = crawl(seed, max_pages=args.max_pages, delay=args.delay, timeout=args.timeout)
    save_outputs(pages, seed, args.max_pages, args.delay)

    print("\nScraping complete")
    print(f"  JSONL   : {OUTPUT_JSONL}")
    print(f"  Markdown: {OUTPUT_MD}")
    print(f"  Metadata: {OUTPUT_META}")


if __name__ == "__main__":
    main()
