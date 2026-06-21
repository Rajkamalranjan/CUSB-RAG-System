"""Scrape current CUSB syllabus PDFs from the official syllabus page.

This scraper discovers PDF links from the live "Course Structure and Syllabus"
page instead of relying on older hard-coded PDF paths. It writes extracted PDF
text to data/CUSB_syllabus_content.md for the RAG knowledge base.
"""

from __future__ import annotations

import io
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import PyPDF2
import requests
from bs4 import BeautifulSoup


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "CUSB_syllabus_content.md"
INDEX_FILE = BASE_DIR / "data" / "CUSB_syllabus.md"
SYLLABUS_PAGE = (
    "https://www.cusb.ac.in/index.php?"
    "Itemid=195&id=119&option=com_content&view=article"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CUSB-RAG-Syllabus-Scraper/1.0)"}


DEPARTMENT_SLUGS = {
    "teacher_edu": "Department of Teacher Education",
    "geology": "Department of Geology",
    "bioinfo": "Department of Bioinformatics",
    "geography": "Department of Geography",
    "agriculture": "Department of Agriculture",
    "commerce_bstudies": "Department of Commerce and Business Studies",
    "biotechonology": "Department of Biotechnology",
    "eco_studies": "Department of Economic Studies and Policies",
    "life_science": "Department of Life Science",
    "chemistry": "Department of Chemistry",
    "psychological_sciences": "Department of Psychological Sciences",
    "physics": "Department of Physics",
}


def clean_text(value: str) -> str:
    """Normalize whitespace for scraped link text and PDF text."""
    return re.sub(r"\s+", " ", value).strip()


def title_from_url(url: str) -> str:
    """Create a readable title from a PDF URL."""
    name = Path(unquote(urlparse(url).path)).stem
    name = re.sub(r"[_-]+", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()


def department_from_url(url: str) -> str:
    """Infer department from the CUSB PDF URL path."""
    path = unquote(urlparse(url).path).lower()
    for slug, department in DEPARTMENT_SLUGS.items():
        if f"/{slug.lower()}/" in path:
            return department
    return "Central University of South Bihar"


def kind_from_title(title: str, url: str) -> str:
    """Classify the PDF as syllabus, structure, BoS, or other."""
    combined = f"{title} {url}".lower()
    if "board" in combined or "bos" in combined:
        return "Board of Studies"
    if "structure" in combined or "struct" in combined:
        return "Course Structure"
    if "syllabus" in combined or "syll" in combined:
        return "Syllabus"
    return "Academic PDF"


def discover_pdf_links() -> list[dict[str, str]]:
    """Return unique PDF links from the official CUSB syllabus page."""
    response = requests.get(SYLLABUS_PAGE, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    discovered: list[dict[str, str]] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if ".pdf" not in href.lower():
            continue

        full_url = urljoin(SYLLABUS_PAGE, href)
        normalized = full_url.split("#", 1)[0]
        if normalized in seen:
            continue
        seen.add(normalized)

        link_text = clean_text(link.get_text(" ", strip=True))
        title = link_text if link_text else title_from_url(full_url)
        discovered.append(
            {
                "title": title,
                "url": full_url,
                "department": department_from_url(full_url),
                "kind": kind_from_title(title, full_url),
            }
        )

    return discovered


def extract_pdf_text(url: str) -> tuple[str, int]:
    """Download a PDF and extract text from all pages."""
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()

    reader = PyPDF2.PdfReader(io.BytesIO(response.content))
    pages: list[str] = []

    for index, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text()
        except Exception as exc:
            print(f"    Warning: page {index} failed: {exc}")
            continue

        if page_text and page_text.strip():
            text = re.sub(r"\n\s*\n\s*\n+", "\n\n", page_text.strip())
            text = re.sub(r"[ \t]{2,}", " ", text)
            pages.append(f"--- Page {index} ---\n{text}")

    return "\n\n".join(pages).strip(), len(reader.pages)


def write_index(items: list[dict[str, str]]) -> None:
    """Write a compact syllabus link index."""
    lines = [
        "# CUSB Current Syllabus PDF Index\n\n",
        f"Scraped on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        f"Source: {SYLLABUS_PAGE}\n\n",
        f"Total unique PDFs: {len(items)}\n\n",
        "| Department | Type | Title | PDF Link |\n",
        "|------------|------|-------|----------|\n",
    ]

    for item in items:
        lines.append(
            f"| {item['department']} | {item['kind']} | "
            f"{item['title']} | {item['url']} |\n"
        )

    INDEX_FILE.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    print("=" * 70)
    print("CUSB CURRENT SYLLABUS SCRAPER")
    print("=" * 70)
    print(f"Discovering PDF links from: {SYLLABUS_PAGE}")

    items = discover_pdf_links()
    print(f"Found {len(items)} unique PDF links")
    write_index(items)

    content_lines = [
        "# CUSB Syllabus - Complete Content (Extracted from Current PDFs)\n\n",
        f"Scraped on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        f"Source: {SYLLABUS_PAGE}\n\n",
        f"Total unique PDFs discovered: {len(items)}\n\n",
        "=" * 50 + "\n\n",
    ]

    successful = 0
    failed = 0

    for number, item in enumerate(items, start=1):
        print(f"\n[{number}/{len(items)}] {item['department']} - {item['title']}")
        print(f"    {item['url']}")

        try:
            text, page_count = extract_pdf_text(item["url"])
        except Exception as exc:
            text = ""
            page_count = 0
            print(f"    Error: {exc}")

        content_lines.append(f"## {item['title']}\n\n")
        content_lines.append(f"**Department:** {item['department']}\n\n")
        content_lines.append(f"**Type:** {item['kind']}\n\n")
        content_lines.append(f"**PDF Download Link:** {item['url']}\n\n")

        if text:
            content_lines.append(f"**Pages Extracted:** {page_count}\n\n")
            content_lines.append("**Extracted Content:**\n\n")
            content_lines.append("```\n")
            content_lines.append(text)
            content_lines.append("\n```\n\n")
            successful += 1
            print(f"    Extracted {page_count} pages, {len(text)} characters")
        else:
            content_lines.append("*[PDF text extraction returned no readable text.]*\n\n")
            failed += 1
            print(f"    No readable text extracted from {page_count} pages")

        content_lines.append("---\n\n")
        time.sleep(0.25)

    OUTPUT_FILE.write_text("".join(content_lines), encoding="utf-8")

    print("\n" + "=" * 70)
    print("Syllabus scraping complete")
    print(f"Successful text extractions: {successful}/{len(items)}")
    print(f"Failed/empty text extractions: {failed}/{len(items)}")
    print(f"Content output: {OUTPUT_FILE}")
    print(f"Index output: {INDEX_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
