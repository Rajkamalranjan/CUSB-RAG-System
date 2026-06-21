"""Extract PDFs from CUSB About/updates/statutory pages into a new corpus.

Outputs:
    data/CUSB_about_university_pdfs.md
    data/cusb_about_university_pdfs.jsonl
    data/cusb_about_university_pdfs_meta.json
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

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
CACHE_DIR = DATA_DIR / "about_university_pdf_cache"
OUTPUT_MD = DATA_DIR / "CUSB_about_university_pdfs.md"
OUTPUT_JSONL = DATA_DIR / "cusb_about_university_pdfs.jsonl"
OUTPUT_META = DATA_DIR / "cusb_about_university_pdfs_meta.json"
DISCOVERY_CACHE = DATA_DIR / "about_university_discovered_preview.json"

USER_AGENT = "CUSB-RAG-AboutUniversityPDFExtractor/1.0"
EXTRACTOR_NAME = "CUSB ABOUT/STATUTORY/UPDATES PDF EXTRACTOR"
CORPUS_TITLE = "CUSB About, Statutory, Notices, Events PDF Extracts"
ID_PREFIX = "about_pdf_"
PAGE_ID_PREFIX = "about_page_"
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "0"))
MIN_TEXT_CHARS = 120
MIN_PAGE_TEXT_CHARS = int(os.getenv("MIN_PAGE_TEXT_CHARS", "40"))
OCR_DPI = int(os.getenv("OCR_DPI", "240"))
OCR_LANG = os.getenv("OCR_LANG", "eng")
OCR_ROTATION_RETRY = os.getenv("OCR_ROTATION_RETRY", "true").lower() in {"1", "true", "yes"}
OCR_ENGINE = os.getenv("OCR_ENGINE", "tesseract").lower()
SKIP_LEGACY_HINDI_TEXT = os.getenv("SKIP_LEGACY_HINDI_TEXT", "true").lower() in {"1", "true", "yes"}
OCR_CONFIGS = [
    config.strip()
    for config in os.getenv(
        "OCR_CONFIGS",
        "--oem 1 --psm 3 -c preserve_interword_spaces=1",
    ).split("||")
    if config.strip()
]
MAX_CHILD_PAGES_PER_SECTION = int(os.getenv("MAX_CHILD_PAGES_PER_SECTION", "250"))

TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
POPLER_BIN = Path(r"C:\Users\alamj\poppler-26.02.0\Library\bin")
PADDLE_OCR = None

SEED_PAGES = [
    ("The University", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=156&Itemid=104"),
    ("Central Universities Act, 2009", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=2&Itemid=105"),
    ("History and Development", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=91&Itemid=106"),
    ("Statutes & Ordinances", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=4&Itemid=107"),
    ("Vision & Mission", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=5&Itemid=108"),
    ("Regulation and Policy Documents", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=6&Itemid=109"),
    ("Salient Features and Best Practices", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=7&Itemid=110"),
    ("Annual Reports and Annual Accounts", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=8&Itemid=111"),
    ("University Kulgeet", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=9&Itemid=112"),
    ("CUSB Logo", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=10&Itemid=113"),
    ("How to Reach CUSB", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=11&Itemid=114"),
    ("The Court", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=12&Itemid=115"),
    ("Executive Council", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=13&Itemid=116"),
    ("Academic Council", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=14&Itemid=117"),
    ("Finance Committee", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=15&Itemid=118"),
    ("Tenders", "https://www.cusb.ac.in/index.php?option=com_content&view=category&id=13&Itemid=566"),
    ("Notices", "https://www.cusb.ac.in/index.php?option=com_content&view=category&id=12&Itemid=567"),
    ("Upcoming Events", "https://www.cusb.ac.in/index.php?option=com_content&view=category&id=23&Itemid=568"),
    ("Archived Events", "https://www.cusb.ac.in/index.php?option=com_content&view=category&id=24&Itemid=569"),
    ("Photo Gallery", "https://www.cusb.ac.in/index.php?option=com_phocagallery&view=category&id=2&Itemid=586"),
    ("Recruitment", "https://www.cusb.ac.in/index.php?option=com_content&view=category&id=48&Itemid=587"),
    ("Download", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=445&Itemid=591"),
    ("Recent Event", "https://www.cusb.ac.in/index.php?option=com_content&view=category&id=54&Itemid=615"),
    ("Academic Highlights", "https://www.cusb.ac.in/index.php?option=com_content&view=category&id=57&Itemid=620"),
    ("Circular / Notification / Office Order", "https://www.cusb.ac.in/index.php?option=com_content&view=category&id=56&Itemid=621"),
    ("Foundation Day", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=934&Itemid=704"),
]


@dataclass
class PdfRecord:
    id: str
    title: str
    url: str
    section: str
    section_url: str
    source_page_url: str
    source_page_title: str
    extraction_method: str
    page_count: int
    pages_extracted: int
    text_pages: int
    ocr_pages: int
    char_count: int
    text_sha256: str
    extracted_at_utc: str
    text: str


@dataclass
class WebPageRecord:
    id: str
    record_type: str
    title: str
    url: str
    section: str
    section_url: str
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


def get_paddle_ocr():
    global PADDLE_OCR
    if PADDLE_OCR is not None:
        return PADDLE_OCR
    if OCR_ENGINE not in {"paddle", "paddleocr"}:
        return None
    try:
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR

        PADDLE_OCR = PaddleOCR(
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True,
        )
        print("PaddleOCR GPU engine loaded", flush=True)
    except Exception as exc:
        print(f"PaddleOCR unavailable, falling back to Tesseract: {exc}", flush=True)
        PADDLE_OCR = None
    return PADDLE_OCR


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()


def repair_mojibake(text: str) -> str:
    if not text or not re.search(r"[âÃ€œ€€™“”]", text):
        return text
    try:
        repaired = text.encode("cp1252", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        return text
    if repaired and repaired.count("�") <= text.count("�"):
        return repaired
    return text


def normalize_text(text: str) -> str:
    text = repair_mojibake(text)
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


def has_hindi_ocr_language() -> bool:
    requested_langs = {part.strip().lower() for part in re.split(r"[+,]", OCR_LANG) if part.strip()}
    if "hin" in requested_langs:
        return True
    return (TESSERACT_EXE.parent / "tessdata" / "hin.traineddata").exists()


def looks_like_legacy_hindi_font_text(text: str) -> bool:
    """Detect Hindi PDFs whose embedded text is exposed as legacy font codes.

    Some CUSB/Gazette PDFs render Hindi correctly in a PDF viewer but expose
    glyph codes such as "fo'ofo|ky;" and "vuqnku" through PyPDF. Indexing that
    text hurts retrieval, so we either OCR it with Hindi support or skip it.
    """
    if len(text) < 120:
        return False
    private_use_count = len(re.findall(r"[\uf000-\uf8ff]", text))
    replacement_count = text.count("�") + text.count("\x00")
    if private_use_count > 0 or replacement_count > 10:
        return True
    if re.search(r"\blgk;d\b", text) and re.search(r"\bizk[/\??]?;kid\b|\bih[Œåa]?,p[Œåa]?Mh\b", text):
        return True
    if re.search(r"\bLkadk;", text) and re.search(r"\bfo['’]?ofo\|ky|\bfcgkj\b", text):
        return True
    devanagari_count = len(re.findall(r"[\u0900-\u097F]", text))
    if devanagari_count > max(20, len(text) * 0.03):
        return False
    legacy_patterns = [
        r"\bfo['’]?ofo\|ky",
        r"\bfo\|ky",
        r"\bdsUnzh;",
        r"\bMk[WåŒ]",
        r"\bdqy",
        r"\blgk;d\b",
        r"\bizk[/\??]?;kid\b",
        r"\bih[Œåa]?,p[Œåa]?Mh\b",
        r"\bfcgkj\b",
        r"\bfganw\b",
        r"\bfgUnh\b",
        r"\busg:\b",
        r"\byqxqu\b",
        r"\blekjksg\b",
        r"\bvuqnku\b",
        r"\bvk;ksx\b",
        r"\bf'k\{kd",
        r"\bmPprj\b",
        r"\bfofu;e\b",
        r"\bHkkjr\b",
        r"\bizdkf",
        r"\bfnYyh\b",
        r"\btqykbZ\b",
        r"\bU;wure\b",
        r"\brFkk\b",
        r"\bLrj\b",
    ]
    hits = sum(1 for pattern in legacy_patterns if re.search(pattern, text, flags=re.IGNORECASE))
    symbol_ratio = sum(char in "|;@{}[]¼½‘’^^" for char in text) / max(len(text), 1)
    return hits >= 3 or (hits >= 2 and symbol_ratio > 0.015)


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
            r"\b(university|central|south|bihar|annual|report|account|regulation|policy|council|committee|student|academic|course|department)\b",
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


def paddle_ocr_for_image(image) -> str:
    ocr = get_paddle_ocr()
    if ocr is None:
        return ""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        image.convert("RGB").save(temp_path)
        result = ocr.predict(str(temp_path))
        texts = []
        for item in result or []:
            if isinstance(item, dict):
                texts.extend(str(text) for text in item.get("rec_texts", []) if str(text).strip())
                continue
            data = getattr(item, "json", None)
            if callable(data):
                try:
                    payload = data()
                    texts.extend(str(text) for text in payload.get("res", {}).get("rec_texts", []) if str(text).strip())
                except Exception:
                    pass
            for attr in ("rec_texts", "texts"):
                values = getattr(item, attr, None)
                if values:
                    texts.extend(str(text) for text in values if str(text).strip())
        return clean_ocr_text("\n".join(texts))
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def pdf_id(url: str) -> str:
    return ID_PREFIX + hashlib.sha1(url.encode("utf-8")).hexdigest()[:14]


def page_id(url: str) -> str:
    return PAGE_ID_PREFIX + hashlib.sha1(url.encode("utf-8")).hexdigest()[:14]


def cache_path(url: str) -> Path:
    return CACHE_DIR / f"{pdf_id(url)}.pdf"


def get_page(session: requests.Session, url: str) -> bytes:
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.SSLError:
        response = session.get(url, timeout=30, verify=False)
        response.raise_for_status()
    return response.content


def parse_html(content: bytes) -> BeautifulSoup:
    return BeautifulSoup(content, "html.parser", from_encoding="utf-8")


def page_title(soup: BeautifulSoup, fallback: str) -> str:
    main = (
        soup.find("div", class_="item-page")
        or soup.find("article")
        or soup.find("main")
        or soup.find("div", class_="content")
    )
    title = main.find(["h1", "h2", "h3"]) if main else None
    if not title:
        title = soup.find(["h1", "h2", "h3"])
    if title:
        text = re.sub(r"\s+", " ", title.get_text(" ", strip=True)).strip()
        if text:
            return text
    if soup.title and soup.title.string:
        return re.sub(r"\s+", " ", soup.title.string).strip()
    return fallback


def is_internal_content_page(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.netloc not in {"www.cusb.ac.in", "cusb.ac.in"}:
        return False
    if parsed.path.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".zip", ".doc", ".docx", ".xls", ".xlsx")):
        return False
    query = parse_qs(parsed.query)
    option = query.get("option", [""])[0]
    view = query.get("view", [""])[0]
    return option == "com_content" and view in {"article", "category"}


def collect_scan_pages(session: requests.Session, section: str, seed_url: str) -> list[dict]:
    content = get_page(session, seed_url)
    soup = parse_html(content)
    pages = [{"url": seed_url, "title": page_title(soup, section)}]
    seen = {normalize_url(seed_url)}
    seed_query = parse_qs(urlparse(seed_url).query)
    seed_itemid = seed_query.get("Itemid", [""])[0]
    seed_view = seed_query.get("view", [""])[0]

    if seed_view != "category":
        return pages

    for link in soup.find_all("a", href=True):
        child_url = normalize_url(urljoin(seed_url, link["href"]))
        if child_url in seen or ".pdf" in child_url.lower() or not is_internal_content_page(child_url):
            continue
        child_query = parse_qs(urlparse(child_url).query)
        if seed_itemid and child_query.get("Itemid", [""])[0] != seed_itemid:
            continue
        text = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
        pages.append({"url": child_url, "title": text or child_url})
        seen.add(child_url)
        if len(pages) >= MAX_CHILD_PAGES_PER_SECTION:
            break

    return pages


def extract_webpage_text(soup: BeautifulSoup) -> str:
    soup = BeautifulSoup(str(soup), "html.parser", from_encoding="utf-8")
    for node in soup(["script", "style", "nav", "footer", "header", "form"]):
        node.decompose()
    main = (
        soup.find("div", class_="item-page")
        or soup.find("article")
        or soup.find("main")
        or soup.find("div", class_="content")
        or soup.body
        or soup
    )
    text = main.get_text("\n", strip=True)
    noise_patterns = [
        r"^\[ RTI \].*$",
        r"^Webmail$",
        r"^Quick Links$",
        r"^Copyright reserved.*$",
    ]
    lines = []
    for line in text.splitlines():
        line = normalize_text(line)
        if not line:
            continue
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in noise_patterns):
            continue
        lines.append(line)
    return normalize_text("\n".join(lines))


def discover_pdfs_and_pages(session: requests.Session) -> tuple[list[dict], list[dict], list[dict]]:
    discovered = []
    page_records = []
    failed_pages = []
    seen_pdfs = set()
    seen_pages = set()

    for section, seed_url in SEED_PAGES:
        print(f"Scanning section: {section}", flush=True)
        try:
            pages = collect_scan_pages(session, section, seed_url)
        except Exception as exc:
            print(f"  Failed to scan seed page: {exc}", flush=True)
            failed_pages.append({"section": section, "url": seed_url, "error": str(exc)})
            continue

        section_count = 0
        for page in pages:
            try:
                content = get_page(session, page["url"])
                soup = parse_html(content)
            except Exception as exc:
                failed_pages.append({"section": section, "url": page["url"], "error": str(exc)})
                continue

            page_url = normalize_url(page["url"])
            if page_url not in seen_pages:
                seen_pages.add(page_url)
                text = extract_webpage_text(soup)
                if text:
                    page_records.append(
                        {
                            "section": section,
                            "section_url": seed_url,
                            "title": page.get("title") or page_title(soup, section),
                            "url": page_url,
                            "text": text,
                        }
                    )

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if ".pdf" not in href.lower():
                    continue
                pdf_url = normalize_url(urljoin(page["url"], href))
                if pdf_url in seen_pdfs:
                    continue
                seen_pdfs.add(pdf_url)
                title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
                if not title:
                    title = pdf_url.rsplit("/", 1)[-1]
                discovered.append(
                    {
                        "section": section,
                        "section_url": seed_url,
                        "source_page_url": page["url"],
                        "source_page_title": page["title"],
                        "title": title,
                        "url": pdf_url,
                    }
                )
                section_count += 1
            time.sleep(0.05)

        print(f"  Pages scanned: {len(pages)} | PDF links found: {section_count}", flush=True)
        time.sleep(0.2)
    return discovered, page_records, failed_pages


def discover_pdfs(session: requests.Session) -> tuple[list[dict], list[dict]]:
    pdfs, _pages, failed_pages = discover_pdfs_and_pages(session)
    return pdfs, failed_pages


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
    if OCR_ENGINE in {"paddle", "paddleocr"}:
        paddle_text = paddle_ocr_for_image(images[0])
        if ocr_quality_score(paddle_text) >= 80:
            return paddle_text
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
        legacy_hindi_text = looks_like_legacy_hindi_font_text(page_text)
        if legacy_hindi_text and SKIP_LEGACY_HINDI_TEXT and not has_hindi_ocr_language():
            page_text = ""
            method = "legacy_hindi_skipped"
        elif len(page_text) < MIN_PAGE_TEXT_CHARS or legacy_hindi_text:
            if ocr_pages >= ocr_limit:
                page_text = "[OCR skipped: OCR_MAX_PAGES limit reached]"
                method = "ocr_skipped"
            else:
                page_text = ocr_single_page(content, index, poppler_path)
                method = "ocr"
        page_text = normalize_text(page_text)
        if page_text:
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


def write_outputs(records: list[PdfRecord], page_records: list[WebPageRecord], failed: list[dict], failed_pages: list[dict]) -> None:
    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for record in page_records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    md = [
        f"# {CORPUS_TITLE}\n\n",
        f"Extracted at UTC: {datetime.now(timezone.utc).isoformat()}\n\n",
        f"PDF records extracted: {len(records)}\n\n",
        f"Website page records extracted: {len(page_records)}\n\n",
        f"PDF records failed: {len(failed)}\n\n",
        f"Pages failed while discovering links: {len(failed_pages)}\n\n",
        f"OCR max pages per PDF: {OCR_MAX_PAGES}\n\n",
        "---\n\n",
    ]
    if page_records:
        md.append("## Website Page Text\n\n")
        for record in page_records:
            md.extend(
                [
                    f"### {record.title}\n\n",
                    f"**Section:** {record.section}\n\n",
                    f"**URL:** {record.url}\n\n",
                    f"**Characters:** {record.char_count}\n\n",
                    "```text\n",
                    record.text,
                    "\n```\n\n---\n\n",
                ]
            )

        md.append("## PDF Extracts\n\n")

    for record in records:
        md.extend(
            [
                f"## {record.title}\n\n",
                f"**Section:** {record.section}\n\n",
                f"**Section URL:** {record.section_url}\n\n",
                f"**Source Page:** {record.source_page_title}\n\n",
                f"**Source Page URL:** {record.source_page_url}\n\n",
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
    if failed_pages:
        md.append("\n## Failed Discovery Pages\n\n")
        for item in failed_pages:
            md.append(f"- {item['section']} | {item['url']} | {item['error']}\n")
    OUTPUT_MD.write_text("".join(md), encoding="utf-8")

    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed_page_count": len(SEED_PAGES),
        "discovered_records": len(records) + len(failed),
        "extracted_records": len(records),
        "webpage_records": len(page_records),
        "failed_records": len(failed),
        "failed_discovery_pages": len(failed_pages),
        "ocr_max_pages": OCR_MAX_PAGES,
        "ocr_dpi": OCR_DPI,
        "ocr_language": OCR_LANG,
        "ocr_engine": OCR_ENGINE,
        "ocr_configs": OCR_CONFIGS,
        "ocr_rotation_retry": OCR_ROTATION_RETRY,
        "min_page_text_chars": MIN_PAGE_TEXT_CHARS,
        "max_child_pages_per_section": MAX_CHILD_PAGES_PER_SECTION,
        "total_text_chars": sum(record.char_count for record in records) + sum(record.char_count for record in page_records),
        "total_pdf_text_chars": sum(record.char_count for record in records),
        "total_webpage_text_chars": sum(record.char_count for record in page_records),
        "total_text_pages": sum(record.text_pages for record in records),
        "total_ocr_pages": sum(record.ocr_pages for record in records),
        "outputs": {
            "markdown": str(OUTPUT_MD.relative_to(BASE_DIR)),
            "jsonl": str(OUTPUT_JSONL.relative_to(BASE_DIR)),
            "metadata": str(OUTPUT_META.relative_to(BASE_DIR)),
        },
        "seed_pages": [{"section": section, "url": url} for section, url in SEED_PAGES],
        "failed": failed,
        "failed_pages": failed_pages,
    }
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    poppler_path = configure_ocr()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print("=" * 70, flush=True)
    print(EXTRACTOR_NAME, flush=True)
    print("=" * 70, flush=True)

    if DISCOVERY_CACHE.exists() and os.getenv("REFRESH_DISCOVERY", "0") != "1":
        cached = json.loads(DISCOVERY_CACHE.read_text(encoding="utf-8"))
        pdfs = cached.get("pdfs", [])
        discovered_pages = cached.get("pages", [])
        failed_pages = cached.get("failed_pages", [])
        print(f"Loaded discovery cache: {DISCOVERY_CACHE}", flush=True)
    else:
        pdfs, discovered_pages, failed_pages = discover_pdfs_and_pages(session)
        DISCOVERY_CACHE.write_text(
            json.dumps({"pdfs": pdfs, "pages": discovered_pages, "failed_pages": failed_pages}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"\nTotal unique PDF links discovered: {len(pdfs)}", flush=True)
    print(f"Total website pages discovered: {len(discovered_pages)}", flush=True)

    records: list[PdfRecord] = []
    page_records: list[WebPageRecord] = []
    failed: list[dict] = []
    processed_urls = set()

    if OUTPUT_JSONL.exists() and os.getenv("RESUME_EXTRACTION", "1") != "0":
        reextract_partial = os.getenv("REEXTRACT_PARTIAL", "0") == "1"
        reextract_webpages = os.getenv("REEXTRACT_WEBPAGES", "0") == "1"
        with OUTPUT_JSONL.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get("record_type") == "webpage_text":
                    if reextract_webpages:
                        continue
                    page_records.append(WebPageRecord(**item))
                    processed_urls.add(item["url"])
                    continue
                item.setdefault("source_page_url", item.get("section_url", ""))
                item.setdefault("source_page_title", item.get("section", ""))
                item.setdefault("text_pages", item.get("pages_extracted", 0) if item.get("extraction_method") == "pypdf" else 0)
                item.setdefault("ocr_pages", item.get("pages_extracted", 0) if item.get("extraction_method") == "ocr" else 0)
                if reextract_partial and item.get("pages_extracted", 0) < item.get("page_count", 0):
                    continue
                records.append(PdfRecord(**item))
                processed_urls.add(item["url"])
        if OUTPUT_META.exists():
            meta = json.loads(OUTPUT_META.read_text(encoding="utf-8"))
            for item in meta.get("failed", []):
                failed.append(item)
                processed_urls.add(item["url"])
        print(
            f"Resuming from checkpoint: {len(page_records)} pages, {len(records)} PDFs, {len(failed)} failed",
            flush=True,
        )

    for item in discovered_pages:
        if item["url"] in processed_urls:
            continue
        text = normalize_text(item["text"])
        if not text:
            continue
        record = WebPageRecord(
            id=page_id(item["url"]),
            record_type="webpage_text",
            title=item["title"],
            url=item["url"],
            section=item["section"],
            section_url=item["section_url"],
            char_count=len(text),
            text_sha256=text_hash(text),
            extracted_at_utc=datetime.now(timezone.utc).isoformat(),
            text=text,
        )
        page_records.append(record)
        processed_urls.add(record.url)
        write_outputs(records, page_records, failed, failed_pages)

    for index, item in enumerate(pdfs, start=1):
        if item["url"] in processed_urls:
            continue
        print(f"\n[{index}/{len(pdfs)}] {item['section']} - {item['title']}", flush=True)
        print(f"  {item['url']}", flush=True)
        try:
            content = download_pdf(session, item["url"])
            text, page_count, pages_extracted, text_pages, ocr_pages, method = extract_hybrid(content, poppler_path)

            if not text:
                raise ValueError("No text extracted")

            record = PdfRecord(
                id=pdf_id(item["url"]),
                title=item["title"],
                url=item["url"],
                section=item["section"],
                section_url=item["section_url"],
                source_page_url=item["source_page_url"],
                source_page_title=item["source_page_title"],
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
            print(
                f"  Extracted {record.char_count} chars "
                f"from {record.pages_extracted}/{record.page_count} pages "
                f"({record.text_pages} text, {record.ocr_pages} OCR, {method})",
                flush=True,
            )
            write_outputs(records, page_records, failed, failed_pages)
        except Exception as exc:
            print(f"  Failed: {exc}", flush=True)
            failed.append({**item, "error": str(exc)})
            write_outputs(records, page_records, failed, failed_pages)
        time.sleep(0.15)

    write_outputs(records, page_records, failed, failed_pages)
    print("\nExtraction complete", flush=True)
    print(f"  Web pages extracted: {len(page_records)}", flush=True)
    print(f"  PDFs extracted: {len(records)}", flush=True)
    print(f"  Failed: {len(failed)}", flush=True)
    print(f"  Discovery page failures: {len(failed_pages)}", flush=True)
    print(f"  Markdown: {OUTPUT_MD}", flush=True)
    print(f"  JSONL: {OUTPUT_JSONL}", flush=True)
    print(f"  Metadata: {OUTPUT_META}", flush=True)


if __name__ == "__main__":
    main()
