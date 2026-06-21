"""Hybrid extract PDFs from data/manual_pdfs.

The extractor uses embedded PDF text first. If a page has no useful text layer,
it falls back to OCR for that page and marks the page as OCR-derived.

Outputs:
    data/CUSB_manual_syllabus_pdfs.md
    data/cusb_manual_syllabus_pdfs.jsonl
    data/cusb_manual_syllabus_pdfs_meta.json
"""

from __future__ import annotations

import hashlib
import argparse
import io
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from PIL import ImageFilter, ImageOps
from PyPDF2 import PdfReader


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "manual_pdfs"
OUTPUT_MD = DATA_DIR / "CUSB_manual_syllabus_pdfs.md"
OUTPUT_JSONL = DATA_DIR / "cusb_manual_syllabus_pdfs.jsonl"
OUTPUT_META = DATA_DIR / "cusb_manual_syllabus_pdfs_meta.json"
EXTRACTOR_NAME = "CUSB MANUAL SYLLABUS HYBRID PDF EXTRACTOR"
CORPUS_TITLE = "CUSB Manual Syllabus PDF Extracts"
ID_PREFIX = "manual_syllabus_pdf_"
ENABLE_FEE_TABLES = os.getenv("ENABLE_FEE_TABLES", "0").lower() in {"1", "true", "yes"}

TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
POPLER_BIN = Path(r"C:\Users\alamj\poppler-26.02.0\Library\bin")

MIN_PAGE_TEXT_CHARS = int(os.getenv("MIN_PAGE_TEXT_CHARS", "40"))
OCR_DPI = int(os.getenv("OCR_DPI", "240"))
OCR_LANG = os.getenv("OCR_LANG", "eng")
OCR_MAX_PAGES_PER_PDF = int(os.getenv("OCR_MAX_PAGES_PER_PDF", "0"))
OCR_CONFIG = os.getenv(
    "OCR_CONFIG",
    "--oem 1 --psm 6 -c preserve_interword_spaces=1",
)
OCR_ROTATION_RETRY = os.getenv("OCR_ROTATION_RETRY", "true").lower() in {"1", "true", "yes"}
OCR_CONFIGS = [
    config.strip()
    for config in os.getenv(
        "OCR_CONFIGS",
        "--oem 1 --psm 3 -c preserve_interword_spaces=1||--oem 1 --psm 4 -c preserve_interword_spaces=1||--oem 1 --psm 6 -c preserve_interword_spaces=1",
    ).split("||")
    if config.strip()
]


@dataclass
class PdfRecord:
    id: str
    title: str
    file_path: str
    extraction_method: str
    page_count: int
    pages_extracted: int
    ocr_pages: int
    text_pages: int
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


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def pdf_id(path: Path) -> str:
    rel = str(path.relative_to(BASE_DIR)).replace("\\", "/")
    return ID_PREFIX + hashlib.sha1(rel.encode("utf-8")).hexdigest()[:14]


def norm_rel_path(value: str) -> str:
    return value.replace("\\", "/")


def clean_title(path: Path) -> str:
    title = path.stem.replace("_", " ")
    return re.sub(r"\s+", " ", title).strip()


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def looks_like_fee_row(line: str) -> bool:
    fee_words = r"(fee|deposit|charge|charges|total|tuition|laboratory|library|medical|sports|student|identity|alumni|corpus|development|examination|evaluation|security|registration|enrolment|enrollment)"
    return bool(re.search(fee_words, line, flags=re.IGNORECASE)) and len(re.findall(r"\d[\d,]*", line)) >= 2


def fee_row_from_line(line: str) -> tuple[str, list[str]] | None:
    cleaned = re.sub(r"\s+", " ", line).strip()
    if not looks_like_fee_row(cleaned):
        return None
    match = re.search(r"\d[\d,]*", cleaned)
    if not match:
        return None
    label = cleaned[: match.start()].strip(" :-|")
    if not label or len(label) > 120:
        return None
    values = re.findall(r"\d[\d,]*(?:\.\d+)?", cleaned[match.start() :])
    if len(values) < 2:
        return None
    return label, values


def extracted_fee_tables(text: str) -> str:
    rows: list[tuple[str, list[str]]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for line in text.splitlines():
        parsed = fee_row_from_line(line)
        if not parsed:
            continue
        key = (parsed[0].lower(), tuple(parsed[1]))
        if key in seen:
            continue
        seen.add(key)
        rows.append(parsed)

    strong_fee_labels = (
        "tuition fee",
        "laboratory fee",
        "computer lab fee",
        "evaluation fee",
        "examination fee",
        "total fee",
        "semester fee",
        "course fee",
        "admission fee",
    )
    has_real_fee_row = any(
        any(label.lower().startswith(prefix) or prefix in label.lower() for prefix in strong_fee_labels)
        for label, _values in rows
    )
    if not rows or not has_real_fee_row:
        return ""

    groups: list[list[tuple[str, list[str]]]] = []
    current: list[tuple[str, list[str]]] = []
    current_width = 0
    for row in rows:
        width = len(row[1])
        if current and width != current_width:
            groups.append(current)
            current = []
        current.append(row)
        current_width = width
    if current:
        groups.append(current)

    parts: list[str] = []
    for group_index, group in enumerate(groups, start=1):
        width = max(len(values) for _label, values in group)
        headers = ["Fee Head"] + [f"Amount {index}" for index in range(1, width + 1)]
        parts.append(f"#### Fee Table {group_index}\n\n")
        parts.append("| " + " | ".join(headers) + " |\n")
        parts.append("| " + " | ".join(["---"] * len(headers)) + " |\n")
        for label, values in group:
            padded_values = values + [""] * (width - len(values))
            cells = [markdown_escape(label)] + [markdown_escape(value) for value in padded_values]
            parts.append("| " + " | ".join(cells) + " |\n")
        parts.append("\n")
    return "".join(parts).strip()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def preprocess_ocr_image(image):
    """Improve scanned-page contrast before OCR without changing the source PDF."""
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)
    return image


def clean_ocr_text(text: str) -> str:
    """Light OCR cleanup: remove noise while avoiding aggressive spell correction."""
    text = normalize_text(text)
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"(?<=\w)\n(?=\w)", " ", text)
    text = re.sub(r"[|]{2,}", "|", text)
    text = re.sub(r"[_]{3,}", "___", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def ocr_quality_score(text: str) -> float:
    """Heuristic score to choose the least-garbled OCR output."""
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
            r"\b(course|semester|credit|paper|programme|program|university|department|commerce|business|syllabus|total|marks|core|elective)\b",
            text,
            flags=re.IGNORECASE,
        )
    )
    long_words = len(re.findall(r"\b[A-Za-z]{4,}\b", text))
    return (letters * 1.5 + digits * 0.3 + common_words * 20 + long_words * 2) - (junk * 1.2)


def run_tesseract(image, config: str) -> str:
    return clean_ocr_text(pytesseract.image_to_string(image, lang=OCR_LANG, config=config))


def detect_pil_rotation(image) -> int:
    """Return a PIL counter-clockwise rotation angle using Tesseract OSD."""
    try:
        osd = pytesseract.image_to_osd(image)
    except Exception:
        return 0
    match = re.search(r"Rotate:\s*(\d+)", osd)
    if not match:
        return 0
    # Tesseract reports clockwise correction; PIL rotate is counter-clockwise.
    return (360 - int(match.group(1))) % 360


def best_ocr_for_image(image, angles: list[int]) -> str:
    best_text = ""
    best_score = float("-inf")
    for angle in angles:
        candidate_image = image.rotate(angle, expand=True) if angle else image
        for config in OCR_CONFIGS:
            candidate = run_tesseract(candidate_image, config)
            score = ocr_quality_score(candidate)
            if score > best_score:
                best_text = candidate
                best_score = score
    return best_text


def ocr_page(path: Path, page_number: int, poppler_path: str | None) -> str:
    images = convert_from_path(
        str(path),
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
        fallback_angles = [0, 90, 180, 270]
        text = best_ocr_for_image(image, fallback_angles)
    return text


def extract_pdf(path: Path, poppler_path: str | None) -> tuple[str, int, int, int, int]:
    reader = PdfReader(str(path))
    parts: list[str] = []
    text_pages = 0
    ocr_pages = 0
    pages_extracted = 0

    for index, page in enumerate(reader.pages, start=1):
        try:
            page_text = normalize_text(page.extract_text() or "")
        except Exception as exc:
            page_text = f"[Page {index} embedded text extraction failed: {exc}]"

        method = "text"
        if len(page_text) < MIN_PAGE_TEXT_CHARS:
            if OCR_MAX_PAGES_PER_PDF and ocr_pages >= OCR_MAX_PAGES_PER_PDF:
                page_text = "[OCR skipped: OCR_MAX_PAGES_PER_PDF limit reached]"
                method = "ocr_skipped"
            else:
                page_text = ocr_page(path, index, poppler_path)
                method = "ocr"

        page_text = normalize_text(page_text)
        if page_text:
            pages_extracted += 1
            if method == "ocr":
                ocr_pages += 1
            elif method == "text":
                text_pages += 1
            parts.append(f"--- Page {index} [{method}] ---\n{page_text}")

    return normalize_text("\n\n".join(parts)), len(reader.pages), pages_extracted, text_pages, ocr_pages


def load_existing() -> tuple[list[PdfRecord], set[str]]:
    records: list[PdfRecord] = []
    done: set[str] = set()
    if not OUTPUT_JSONL.exists() or os.getenv("RESUME_EXTRACTION", "1") == "0":
        return records, done
    with OUTPUT_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            records.append(PdfRecord(**item))
            done.add(norm_rel_path(item["file_path"]))
    return records, done


def write_outputs(records: list[PdfRecord], failed: list[dict]) -> None:
    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    md = [
        f"# {CORPUS_TITLE}\n\n",
        f"Extracted at UTC: {datetime.now(timezone.utc).isoformat()}\n\n",
        f"Input folder: `{INPUT_DIR.relative_to(BASE_DIR)}`\n\n",
        f"PDF records extracted: {len(records)}\n\n",
        f"PDF records failed: {len(failed)}\n\n",
        f"OCR language: `{OCR_LANG}`\n\n",
        "Extraction method: embedded text first, OCR only for pages without readable embedded text.\n\n",
        "---\n\n",
    ]
    for record in records:
        fee_tables = extracted_fee_tables(record.text) if ENABLE_FEE_TABLES else ""
        md.extend(
            [
                f"## {record.title}\n\n",
                f"**File:** {record.file_path}\n\n",
                f"**Extraction Method:** {record.extraction_method}\n\n",
                f"**Pages in PDF:** {record.page_count}\n\n",
                f"**Pages Extracted:** {record.pages_extracted}\n\n",
                f"**Embedded Text Pages:** {record.text_pages}\n\n",
                f"**OCR Pages:** {record.ocr_pages}\n\n",
                f"**Characters:** {record.char_count}\n\n",
            ]
        )
        if fee_tables:
            md.extend(
                [
                    "### Extracted Fee Tables\n\n",
                    fee_tables,
                    "\n\n",
                ]
            )
        md.extend(
            [
                "### Extracted Text\n\n",
                "```text\n",
                record.text,
                "\n```\n\n---\n\n",
            ]
        )
    if failed:
        md.append("## Failed PDFs\n\n")
        for item in failed:
            md.append(f"- {item['file_path']} | {item['error']}\n")
    OUTPUT_MD.write_text("".join(md), encoding="utf-8")

    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_folder": str(INPUT_DIR.relative_to(BASE_DIR)),
        "discovered_records": len(records) + len(failed),
        "extracted_records": len(records),
        "failed_records": len(failed),
        "total_text_chars": sum(record.char_count for record in records),
        "total_text_pages": sum(record.text_pages for record in records),
        "total_ocr_pages": sum(record.ocr_pages for record in records),
        "ocr_language": OCR_LANG,
        "ocr_dpi": OCR_DPI,
        "ocr_config": OCR_CONFIG,
        "ocr_configs": OCR_CONFIGS,
        "ocr_rotation_retry": OCR_ROTATION_RETRY,
        "min_page_text_chars": MIN_PAGE_TEXT_CHARS,
        "outputs": {
            "markdown": str(OUTPUT_MD.relative_to(BASE_DIR)),
            "jsonl": str(OUTPUT_JSONL.relative_to(BASE_DIR)),
            "metadata": str(OUTPUT_META.relative_to(BASE_DIR)),
        },
        "failed": failed,
    }
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Extract {CORPUS_TITLE} with page-level OCR fallback.")
    parser.add_argument(
        "--pdf",
        help="Extract only one PDF. Match is case-insensitive and can be a full filename or part of a filename.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract even if this PDF is already present in the JSONL checkpoint.",
    )
    args = parser.parse_args()

    poppler_path = configure_ocr()
    pdfs = sorted(INPUT_DIR.glob("*.pdf"), key=lambda p: p.name.lower())
    if args.pdf:
        needle = args.pdf.lower()
        exact_matches = [path for path in pdfs if needle == path.name.lower()]
        pdfs = exact_matches or [path for path in pdfs if needle in path.name.lower()]
        if not pdfs:
            available = "\n".join(f"- {path.name}" for path in sorted(INPUT_DIR.glob("*.pdf"), key=lambda p: p.name.lower()))
            raise SystemExit(f"No PDF matched: {args.pdf}\n\nAvailable PDFs:\n{available}")
        if len(pdfs) > 1:
            matches = "\n".join(f"- {path.name}" for path in pdfs)
            raise SystemExit(f"Multiple PDFs matched: {args.pdf}\nPlease be more specific:\n{matches}")

    records, done = load_existing()
    if args.force:
        selected_paths = {norm_rel_path(str(path.relative_to(BASE_DIR))) for path in pdfs}
        records = [record for record in records if norm_rel_path(record.file_path) not in selected_paths]
        done = {norm_rel_path(record.file_path) for record in records}
    failed: list[dict] = []

    print("=" * 70, flush=True)
    print(EXTRACTOR_NAME, flush=True)
    print("=" * 70, flush=True)
    print(f"PDF files found: {len(pdfs)}", flush=True)
    if args.pdf:
        print(f"Single PDF mode: {pdfs[0].name}", flush=True)
    if done:
        print(f"Resuming from checkpoint: {len(done)} PDFs already extracted", flush=True)

    for index, path in enumerate(pdfs, start=1):
        rel_path = str(path.relative_to(BASE_DIR))
        if norm_rel_path(rel_path) in done:
            continue
        print(f"\n[{index}/{len(pdfs)}] {rel_path}", flush=True)
        try:
            text, page_count, pages_extracted, text_pages, ocr_pages = extract_pdf(path, poppler_path)
            if not text:
                raise ValueError("No text extracted")
            method = "hybrid" if ocr_pages and text_pages else ("ocr" if ocr_pages else "embedded_pdf_text")
            record = PdfRecord(
                id=pdf_id(path),
                title=clean_title(path),
                file_path=rel_path,
                extraction_method=method,
                page_count=page_count,
                pages_extracted=pages_extracted,
                ocr_pages=ocr_pages,
                text_pages=text_pages,
                char_count=len(text),
                text_sha256=text_hash(text),
                extracted_at_utc=datetime.now(timezone.utc).isoformat(),
                text=text,
            )
            records.append(record)
            done.add(rel_path)
            print(
                f"  Extracted {record.char_count} chars from "
                f"{record.pages_extracted}/{record.page_count} pages "
                f"({record.text_pages} text, {record.ocr_pages} OCR)",
                flush=True,
            )
            write_outputs(records, failed)
        except Exception as exc:
            print(f"  Failed: {exc}", flush=True)
            failed.append({"file_path": rel_path, "error": str(exc)})
            write_outputs(records, failed)

    write_outputs(records, failed)
    print("\nExtraction complete", flush=True)
    print(f"  Extracted: {len(records)}", flush=True)
    print(f"  Failed: {len(failed)}", flush=True)
    print(f"  Markdown: {OUTPUT_MD}", flush=True)
    print(f"  JSONL: {OUTPUT_JSONL}", flush=True)
    print(f"  Metadata: {OUTPUT_META}", flush=True)


if __name__ == "__main__":
    main()
