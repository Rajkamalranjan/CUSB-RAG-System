"""Extract PDFs from selected CUSB student/academic pages into a new corpus.

Outputs:
    data/CUSB_student_academic_pdfs.md
    data/cusb_student_academic_pdfs.jsonl
    data/cusb_student_academic_pdfs_meta.json

This handles direct PDF text extraction and OCR fallback for scanned PDFs.
OCR fallback is capped by OCR_MAX_PAGES to avoid very long runs on large scanned
documents. The cap is recorded in each extracted record.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import time
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pytesseract
import requests
import urllib3
from bs4 import BeautifulSoup
from pdf2image import convert_from_bytes
from PIL import ImageFilter, ImageOps
from PyPDF2 import PdfReader


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "student_academic_pdf_cache"
OUTPUT_MD = DATA_DIR / "CUSB_student_academic_pdfs.md"
OUTPUT_JSONL = DATA_DIR / "cusb_student_academic_pdfs.jsonl"
OUTPUT_META = DATA_DIR / "cusb_student_academic_pdfs_meta.json"

USER_AGENT = "CUSB-RAG-StudentAcademicPDFExtractor/1.0"
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "0"))
MIN_TEXT_CHARS = 120
MIN_PAGE_TEXT_CHARS = int(os.getenv("MIN_PAGE_TEXT_CHARS", "40"))
OCR_DPI = int(os.getenv("OCR_DPI", "240"))
OCR_LANG = os.getenv("OCR_LANG", "eng")
OCR_ROTATION_RETRY = os.getenv("OCR_ROTATION_RETRY", "true").lower() in {"1", "true", "yes"}
OCR_CONFIGS = [
    config.strip()
    for config in os.getenv(
        "OCR_CONFIGS",
        "--oem 1 --psm 3 -c preserve_interword_spaces=1",
    ).split("||")
    if config.strip()
]

TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
POPLER_BIN = Path(r"C:\Users\alamj\poppler-26.02.0\Library\bin")

SEED_PAGES = [
    ("Department & Programmes", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=535&Itemid=190"),
    ("Academics/Examination Notices", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=76&Itemid=191"),
    ("Semester Exam Schedule", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=77&Itemid=192"),
    ("Ordinance/ Manual/ Regulation", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=78&Itemid=193"),
    ("Semester Result", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=904&Itemid=194"),
    ("Prospectus", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=82&Itemid=197"),
    ("Convocation", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=625&Itemid=209"),
    ("Download (Format/Performa)", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=455&Itemid=619"),
    ("Course Structure and Syllabus", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=119&Itemid=195"),
    ("Scholarship and Fellowship", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=81&Itemid=196"),
    ("Hostel", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=451&Itemid=198"),
    ("Anti-Ragging", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=84&Itemid=199"),
    ("Alumni", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=85&Itemid=200"),
    ("DACE", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=86&Itemid=201"),
    ("Capacity Development and Skill Enhancement Programme", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=525&Itemid=202"),
    ("Placement Cell", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=88&Itemid=203"),
    ("Students Counselling and Well- being Centre", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=89&Itemid=204"),
    ("NSS", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=495&Itemid=205"),
    ("NCC", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=92&Itemid=206"),
    ("Extracurricular Activities", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=93&Itemid=207"),
    ("Code of Ethics", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=96&Itemid=210"),
    ("Grievance Redressal Committee for Students", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=97&Itemid=211"),
]


@dataclass
class PdfRecord:
    id: str
    title: str
    url: str
    section: str
    section_url: str
    extraction_method: str
    page_count: int
    pages_extracted: int
    text_pages: int
    ocr_pages: int
    char_count: int
    text_sha256: str
    extracted_at_utc: str
    text: str


def configure_ocr() -> str | None:
    if TESSERACT_EXE.exists():
        pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)
    if POPLER_BIN.exists():
        os.environ["PATH"] = f"{POPLER_BIN};{os.environ.get('PATH', '')}"
        return str(POPLER_BIN)
    return None


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()


def clean_ocr_text(text: str) -> str:
    text = normalize_text(text)
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"(?<=\w)\n(?=\w)", " ", text)
    text = re.sub(r"[|]{2,}", "|", text)
    text = re.sub(r"[_]{3,}", "___", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def preprocess_ocr_image(image):
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)
    return image


def ocr_quality_score(text: str) -> float:
    if not text:
        return 0.0
    chars = [char for char in text if not char.isspace()]
    if not chars:
        return 0.0
    letters = sum(char.isalpha() for char in chars)
    digits = sum(char.isdigit() for char in chars)
    junk = sum(char in "|\\/_=<>[]{}~^`" for char in chars)
    common_words = len(
        re.findall(
            r"\b(course|semester|student|academic|university|department|programme|program|notice|exam|examination|syllabus|admission|hostel)\b",
            text,
            flags=re.IGNORECASE,
        )
    )
    long_words = len(re.findall(r"\b[A-Za-z]{4,}\b", text))
    return (letters * 1.5 + digits * 0.3 + common_words * 20 + long_words * 2) - (junk * 1.2)


def detect_pil_rotation(image) -> int:
    try:
        osd = pytesseract.image_to_osd(image)
    except Exception:
        return 0
    match = re.search(r"Rotate:\s*(\d+)", osd)
    if not match:
        return 0
    return (360 - int(match.group(1))) % 360


def best_ocr_for_image(image, angles: list[int]) -> str:
    best_text = ""
    best_score = float("-inf")
    for angle in angles:
        candidate_image = image.rotate(angle, expand=True) if angle else image
        for config in OCR_CONFIGS:
            candidate = clean_ocr_text(
                pytesseract.image_to_string(candidate_image, lang=OCR_LANG, config=config)
            )
            score = ocr_quality_score(candidate)
            if score > best_score:
                best_text = candidate
                best_score = score
    return best_text


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def pdf_id(url: str) -> str:
    return "student_pdf_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:14]


def cache_path(url: str) -> Path:
    return CACHE_DIR / f"{pdf_id(url)}.pdf"


def discover_pdfs(session: requests.Session) -> list[dict]:
    discovered = []
    seen = set()
    for section, page_url in SEED_PAGES:
        print(f"Scanning section: {section}")
        response = session.get(page_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        count = 0
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if ".pdf" not in href.lower():
                continue
            pdf_url = urljoin(page_url, href)
            if pdf_url in seen:
                continue
            seen.add(pdf_url)
            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not title:
                title = pdf_url.rsplit("/", 1)[-1]
            discovered.append(
                {
                    "section": section,
                    "section_url": page_url,
                    "title": title,
                    "url": pdf_url,
                }
            )
            count += 1
        print(f"  PDF links found: {count}")
        time.sleep(0.2)
    return discovered


def download_pdf(session: requests.Session, url: str) -> bytes:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path(url)
    if path.exists():
        return path.read_bytes()

    try:
        response = session.get(url, timeout=60)
        response.raise_for_status()
    except requests.exceptions.SSLError:
        response = session.get(url, timeout=60, verify=False)
        response.raise_for_status()

    content = response.content
    if not content.startswith(b"%PDF"):
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower():
            raise ValueError(f"Not a PDF response: content-type={content_type}")
    path.write_bytes(content)
    return content


def extract_with_pypdf(content: bytes) -> tuple[str, int, int]:
    reader = PdfReader(io.BytesIO(content))
    parts = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:
            page_text = f"[Page {index} extraction failed: {exc}]"
        if page_text.strip():
            parts.append(f"--- Page {index} ---\n{page_text}")
    return normalize_text("\n\n".join(parts)), len(reader.pages), len(reader.pages)


def ocr_single_page(content: bytes, page_number: int, poppler_path: str | None) -> str:
    images = convert_from_bytes(
        content,
        dpi=OCR_DPI,
        first_page=page_number,
        last_page=page_number,
        poppler_path=poppler_path,
        fmt="png",
        thread_count=1,
    )
    if not images:
        return ""
    image = preprocess_ocr_image(images[0])
    osd_angle = detect_pil_rotation(image)
    angles = [osd_angle] if osd_angle else [0]
    text = best_ocr_for_image(image, angles)
    if OCR_ROTATION_RETRY and ocr_quality_score(text) < 120:
        text = best_ocr_for_image(image, [0, 90, 180, 270])
    return text


def extract_hybrid(content: bytes, poppler_path: str | None) -> tuple[str, int, int, int, int, str]:
    reader = PdfReader(io.BytesIO(content))
    page_count = len(reader.pages)
    parts = []
    text_pages = 0
    ocr_pages = 0
    pages_extracted = 0
    ocr_limit = OCR_MAX_PAGES if OCR_MAX_PAGES > 0 else page_count

    for index, page in enumerate(reader.pages, start=1):
        try:
            page_text = normalize_text(page.extract_text() or "")
        except Exception as exc:
            page_text = f"[Page {index} embedded text extraction failed: {exc}]"
        method = "text"
        if len(page_text) < MIN_PAGE_TEXT_CHARS:
            if ocr_pages >= ocr_limit:
                page_text = "[OCR skipped: OCR_MAX_PAGES limit reached]"
                method = "ocr_skipped"
            else:
                page_text = ocr_single_page(content, index, poppler_path)
                method = "ocr"
        page_text = normalize_text(page_text)
        if page_text.strip():
            pages_extracted += 1
            if method == "ocr":
                ocr_pages += 1
            elif method == "text":
                text_pages += 1
            parts.append(f"--- Page {index} [{method}] ---\n{page_text}")

    if ocr_pages and text_pages:
        extraction_method = "hybrid"
    elif ocr_pages:
        extraction_method = "ocr"
    else:
        extraction_method = "pypdf"
    return normalize_text("\n\n".join(parts)), page_count, pages_extracted, text_pages, ocr_pages, extraction_method


def write_outputs(records: list[PdfRecord], failed: list[dict]) -> None:
    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    md = [
        "# CUSB Student and Academic PDF Extracts\n\n",
        f"Extracted at UTC: {datetime.now(timezone.utc).isoformat()}\n\n",
        f"PDF records extracted: {len(records)}\n\n",
        f"PDF records failed: {len(failed)}\n\n",
        f"OCR max pages per PDF: {OCR_MAX_PAGES}\n\n",
        "---\n\n",
    ]
    for record in records:
        md.extend(
            [
                f"## {record.title}\n\n",
                f"**Section:** {record.section}\n\n",
                f"**Section URL:** {record.section_url}\n\n",
                f"**PDF URL:** {record.url}\n\n",
                f"**Extraction Method:** {record.extraction_method}\n\n",
                f"**Pages in PDF:** {record.page_count}\n\n",
                f"**Pages Extracted:** {record.pages_extracted}\n\n",
                f"**Embedded Text Pages:** {record.text_pages}\n\n",
                f"**OCR Pages:** {record.ocr_pages}\n\n",
                f"**Characters:** {record.char_count}\n\n",
                "```text\n",
                record.text,
                "\n```\n\n---\n\n",
            ]
        )
    if failed:
        md.append("## Failed PDFs\n\n")
        for item in failed:
            md.append(f"- {item['section']} | {item['title']} | {item['url']} | {item['error']}\n")
    OUTPUT_MD.write_text("".join(md), encoding="utf-8")

    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed_page_count": len(SEED_PAGES),
        "discovered_records": len(records) + len(failed),
        "extracted_records": len(records),
        "failed_records": len(failed),
        "ocr_max_pages": OCR_MAX_PAGES,
        "ocr_dpi": OCR_DPI,
        "ocr_language": OCR_LANG,
        "ocr_configs": OCR_CONFIGS,
        "ocr_rotation_retry": OCR_ROTATION_RETRY,
        "min_page_text_chars": MIN_PAGE_TEXT_CHARS,
        "total_text_chars": sum(record.char_count for record in records),
        "total_text_pages": sum(record.text_pages for record in records),
        "total_ocr_pages": sum(record.ocr_pages for record in records),
        "outputs": {
            "markdown": str(OUTPUT_MD.relative_to(BASE_DIR)),
            "jsonl": str(OUTPUT_JSONL.relative_to(BASE_DIR)),
            "metadata": str(OUTPUT_META.relative_to(BASE_DIR)),
        },
        "seed_pages": [{"section": section, "url": url} for section, url in SEED_PAGES],
        "failed": failed,
    }
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_existing() -> tuple[list[PdfRecord], list[dict], set[str]]:
    records: list[PdfRecord] = []
    failed: list[dict] = []
    processed: set[str] = set()
    if os.getenv("RESUME_EXTRACTION", "1") == "0" or not OUTPUT_JSONL.exists():
        return records, failed, processed

    with OUTPUT_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            item.setdefault("text_pages", item.get("pages_extracted", 0) if item.get("extraction_method") == "pypdf" else 0)
            item.setdefault("ocr_pages", item.get("pages_extracted", 0) if item.get("extraction_method") == "ocr" else 0)
            record = PdfRecord(**item)
            records.append(record)
            processed.add(record.url)

    if OUTPUT_META.exists():
        meta = json.loads(OUTPUT_META.read_text(encoding="utf-8"))
        for item in meta.get("failed", []):
            failed.append(item)
            if item.get("url"):
                processed.add(item["url"])

    return records, failed, processed


def main() -> None:
    poppler_path = configure_ocr()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print("=" * 70)
    print("CUSB STUDENT/ACADEMIC PDF EXTRACTOR")
    print("=" * 70)

    pdfs = discover_pdfs(session)
    print(f"\nTotal unique PDF links discovered: {len(pdfs)}")

    records, failed, processed_urls = load_existing()
    if processed_urls:
        print(f"Resuming from checkpoint: {len(records)} extracted, {len(failed)} failed")

    for index, item in enumerate(pdfs, start=1):
        if item["url"] in processed_urls:
            continue
        print(f"\n[{index}/{len(pdfs)}] {item['section']} - {item['title']}")
        print(f"  {item['url']}")
        try:
            content = download_pdf(session, item["url"])
            text, page_count, pages_extracted, text_pages, ocr_pages, method = extract_hybrid(
                content,
                poppler_path,
            )

            if not text:
                raise ValueError("No text extracted")

            record = PdfRecord(
                id=pdf_id(item["url"]),
                title=item["title"],
                url=item["url"],
                section=item["section"],
                section_url=item["section_url"],
                extraction_method=method,
                page_count=page_count,
                pages_extracted=pages_extracted,
                text_pages=text_pages,
                ocr_pages=ocr_pages,
                char_count=len(text),
                text_sha256=text_hash(text),
                extracted_at_utc=datetime.now(timezone.utc).isoformat(),
                text=text,
            )
            records.append(record)
            processed_urls.add(record.url)
            print(
                f"  Extracted {record.char_count} chars "
                f"from {record.pages_extracted}/{record.page_count} pages "
                f"({record.text_pages} text, {record.ocr_pages} OCR, {method})"
            )
            write_outputs(records, failed)
        except Exception as exc:
            print(f"  Failed: {exc}")
            failed.append({**item, "error": str(exc)})
            processed_urls.add(item["url"])
            write_outputs(records, failed)
        time.sleep(0.2)

    write_outputs(records, failed)
    print("\nExtraction complete")
    print(f"  Extracted: {len(records)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Markdown: {OUTPUT_MD}")
    print(f"  JSONL: {OUTPUT_JSONL}")
    print(f"  Metadata: {OUTPUT_META}")


if __name__ == "__main__":
    main()
