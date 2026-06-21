"""Extract department-wise syllabus PDFs from data/syllabus.

Outputs:
    data/cusb_manual_syllabus.md
    data/cusb_manual_syllabus.json
    data/cusb_manual_syllabus.jsonl
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PyPDF2 import PdfReader

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "syllabus"
OUTPUT_MD = DATA_DIR / "cusb_manual_syllabus.md"
OUTPUT_JSON = DATA_DIR / "cusb_manual_syllabus.json"
OUTPUT_JSONL = DATA_DIR / "cusb_manual_syllabus.jsonl"

TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
PDFTOPPM_EXE = Path(r"C:\Users\alamj\poppler-26.02.0\Library\bin\pdftoppm.exe")
MIN_PAGE_TEXT_CHARS = 40
OCR_DPI = int(os.getenv("SYLLABUS_OCR_DPI", "260"))
OCR_LANG = os.getenv("SYLLABUS_OCR_LANG", "eng")
OCR_CONFIGS = [
    "--oem 1 --psm 6 -c preserve_interword_spaces=1",
    "--oem 1 --psm 4 -c preserve_interword_spaces=1",
    "--oem 1 --psm 3 -c preserve_interword_spaces=1",
]


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def clean_ocr_text(text: str) -> str:
    text = normalize_text(text)
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"(?<=\w)\n(?=\w)", " ", text)
    text = re.sub(r"[|]{2,}", "|", text)
    text = re.sub(r"[_]{4,}", "___", text)
    return normalize_text(text)


def quality_score(text: str) -> float:
    if not text:
        return 0.0
    chars = [char for char in text if not char.isspace()]
    letters = sum(char.isalpha() for char in chars)
    digits = sum(char.isdigit() for char in chars)
    junk = sum(char in "|\\/_=<>[]{}~^`" for char in chars)
    common = len(
        re.findall(
            r"\b(course|semester|credit|syllabus|programme|program|department|"
            r"university|unit|marks|theory|practical|objective|outcome)\b",
            text,
            flags=re.IGNORECASE,
        )
    )
    return letters * 1.5 + digits * 0.3 + common * 25 - junk * 1.3


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def record_id(path: Path) -> str:
    rel = str(path.relative_to(BASE_DIR)).replace("\\", "/")
    return "manual_syllabus_" + hashlib.sha1(rel.encode("utf-8")).hexdigest()[:14]


def infer_department(path: Path, title_text: str) -> str:
    name = path.name.lower()
    text = title_text.lower()
    if any(token in name for token in ["admin law", "family law", "crimes", "public international", "ios"]):
        return "Department of Law and Governance"
    if "law" in text and "syllabus" in text:
        return "Department of Law and Governance"
    if "m.p.ed" in name or "physical education" in text:
        return "Department of Physical Education"
    if "m_ed" in name or "m.ed" in text or "education" in text:
        return "Department of Teacher Education"
    if "life sc" in name or "life science" in text:
        return "Department of Life Science"
    if "biotechnology" in name or "biotechnology" in text:
        return "Department of Biotechnology"
    if "evs" in name or "environmental" in text:
        return "Department of Environmental Science"
    return "Unclassified Syllabus"


def clean_title(path: Path, first_text: str) -> str:
    candidates = []
    for line in first_text.splitlines()[:40]:
        line = normalize_text(line)
        if 8 <= len(line) <= 140 and not re.fullmatch(r"[\W\d_]+", line):
            candidates.append(line)
    if candidates:
        for candidate in candidates:
            if re.search(r"syllabus|course|law|education|science|programme|semester", candidate, re.I):
                return candidate
    return re.sub(r"\s+", " ", path.stem.replace("_", " ")).strip(" .")


def embedded_page_text(page) -> str:
    try:
        return normalize_text(page.extract_text() or "")
    except Exception:
        return ""


def ocr_page(pdf_path: Path, page_number: int) -> str:
    if not TESSERACT_EXE.exists() or not PDFTOPPM_EXE.exists():
        return "[OCR unavailable: tesseract or pdftoppm was not found]"
    best_text = ""
    best_score = float("-inf")
    with tempfile.TemporaryDirectory(prefix="cusb_syllabus_ocr_") as tmp:
        prefix = Path(tmp) / "page"
        subprocess.run(
            [
                str(PDFTOPPM_EXE),
                "-r",
                str(OCR_DPI),
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-png",
                str(pdf_path),
                str(prefix),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        images = sorted(Path(tmp).glob("page-*.png"))
        if not images:
            return ""
        image = images[0]
        for config in OCR_CONFIGS:
            cmd = [str(TESSERACT_EXE), str(image), "stdout", "-l", OCR_LANG] + config.split()
            result = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            candidate = clean_ocr_text(result.stdout.decode("utf-8", errors="replace"))
            score = quality_score(candidate)
            if score > best_score:
                best_score = score
                best_text = candidate
    return best_text


def extract_pdf(path: Path) -> dict:
    reader = PdfReader(str(path))
    page_parts = []
    text_pages = 0
    ocr_pages = 0

    for page_number, page in enumerate(reader.pages, start=1):
        text = embedded_page_text(page)
        method = "text"
        if len(text) < MIN_PAGE_TEXT_CHARS:
            text = ocr_page(path, page_number)
            method = "ocr"
        text = normalize_text(text)
        if text:
            if method == "ocr":
                ocr_pages += 1
            else:
                text_pages += 1
            page_parts.append(f"--- Page {page_number} [{method}] ---\n{text}")

    full_text = normalize_text("\n\n".join(page_parts))
    title = clean_title(path, full_text)
    department = infer_department(path, full_text[:5000])
    rel_path = str(path.relative_to(BASE_DIR)).replace("\\", "/")
    method = "hybrid" if text_pages and ocr_pages else ("ocr" if ocr_pages else "embedded_pdf_text")

    return {
        "id": record_id(path),
        "department": department,
        "title": title,
        "file_name": path.name,
        "file_path": rel_path,
        "file_sha256": file_hash(path),
        "extraction_method": method,
        "page_count": len(reader.pages),
        "pages_extracted": text_pages + ocr_pages,
        "embedded_text_pages": text_pages,
        "ocr_pages": ocr_pages,
        "char_count": len(full_text),
        "text_sha256": text_hash(full_text),
        "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
        "text": full_text,
    }


def write_outputs(records: list[dict]) -> None:
    records = sorted(records, key=lambda item: (item["department"].lower(), item["title"].lower()))

    OUTPUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    lines = [
        "# CUSB Manual Syllabus Extracts\n\n",
        f"Extracted at UTC: {datetime.now(timezone.utc).isoformat()}\n\n",
        f"Input folder: `{INPUT_DIR.relative_to(BASE_DIR)}`\n\n",
        f"PDF records extracted: {len(records)}\n\n",
        "Grouped department-wise from local syllabus PDFs. Embedded text was used where available; OCR was used only for scanned pages.\n\n",
        "---\n\n",
    ]
    current_department = None
    for record in records:
        if record["department"] != current_department:
            current_department = record["department"]
            lines.append(f"## {current_department}\n\n")
        lines.extend(
            [
                f"### {record['title']}\n\n",
                f"**File:** `{record['file_path']}`\n\n",
                f"**Extraction Method:** `{record['extraction_method']}`\n\n",
                f"**Pages:** {record['pages_extracted']} extracted / {record['page_count']} total "
                f"({record['embedded_text_pages']} text, {record['ocr_pages']} OCR)\n\n",
                f"**Characters:** {record['char_count']}\n\n",
                "```text\n",
                record["text"],
                "\n```\n\n",
            ]
        )
    OUTPUT_MD.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    pdfs = sorted(INPUT_DIR.glob("*.pdf"), key=lambda item: item.name.lower())
    print(f"PDF files found: {len(pdfs)}", flush=True)
    records = []
    for index, path in enumerate(pdfs, start=1):
        print(f"[{index}/{len(pdfs)}] {path.name}", flush=True)
        record = extract_pdf(path)
        records.append(record)
        print(
            f"  {record['char_count']} chars, {record['embedded_text_pages']} text pages, "
            f"{record['ocr_pages']} OCR pages, department: {record['department']}",
            flush=True,
        )
        write_outputs(records)
    write_outputs(records)
    print("Done", flush=True)
    print(f"Markdown: {OUTPUT_MD}", flush=True)
    print(f"JSON: {OUTPUT_JSON}", flush=True)
    print(f"JSONL: {OUTPUT_JSONL}", flush=True)


if __name__ == "__main__":
    main()
