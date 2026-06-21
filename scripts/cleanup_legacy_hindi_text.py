"""Remove legacy-font Hindi extraction noise from about-university outputs."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.extract_about_university_pdfs as extractor
from src.extract_about_university_pdfs import (
    OUTPUT_JSONL,
    OUTPUT_MD,
    OUTPUT_META,
    PdfRecord,
    WebPageRecord,
    looks_like_legacy_hindi_font_text,
    normalize_text,
    text_hash,
    write_outputs,
)

TARGET = os.getenv("CLEANUP_TARGET", "about").lower()
if TARGET in {"facility", "facility_service", "student_corner"}:
    OUTPUT_JSONL = Path("data/cusb_facility_service_pdfs.jsonl").resolve()
    OUTPUT_MD = Path("data/CUSB_facility_service_pdfs.md").resolve()
    OUTPUT_META = Path("data/cusb_facility_service_pdfs_meta.json").resolve()
elif TARGET in {"administration", "admin"}:
    OUTPUT_JSONL = Path("data/cusb_administration_pdfs.jsonl").resolve()
    OUTPUT_MD = Path("data/CUSB_administration_pdfs.md").resolve()
    OUTPUT_META = Path("data/cusb_administration_pdfs_meta.json").resolve()

extractor.OUTPUT_JSONL = OUTPUT_JSONL
extractor.OUTPUT_MD = OUTPUT_MD
extractor.OUTPUT_META = OUTPUT_META


PAGE_RE = re.compile(r"--- Page (?P<number>\d+) \[(?P<method>[^\]]+)\] ---\n", re.MULTILINE)
PRIVATE_FONT_RE = re.compile(r"[\uf000-\uf8ff]")
LEGACY_NOISE_LINE_RE = re.compile(
    r"fo['’]?ofo\|ky|vuqnku\s+vk;ksx|mPprj\s+f'k|lgk;d\s+izk|Lkadk;",
    flags=re.IGNORECASE,
)


def strip_private_font_chars(text: str) -> str:
    return normalize_text(PRIVATE_FONT_RE.sub(" ", text))


def strip_legacy_noise_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if LEGACY_NOISE_LINE_RE.search(line):
            continue
        lines.append(line)
    return normalize_text("\n".join(lines))


def clean_pdf_text(text: str) -> tuple[str, int]:
    matches = list(PAGE_RE.finditer(text))
    if not matches:
        return ("", 1) if looks_like_legacy_hindi_font_text(text) else (text, 0)

    kept_parts: list[str] = []
    dropped = 0
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if looks_like_legacy_hindi_font_text(body):
            dropped += 1
            continue
        body = strip_legacy_noise_lines(strip_private_font_chars(body))
        kept_parts.append(match.group(0).rstrip() + "\n" + body)
    return normalize_text("\n\n".join(part for part in kept_parts if part.strip())), dropped


def clean_webpage_text(text: str) -> tuple[str, int]:
    kept_lines: list[str] = []
    dropped = 0
    for line in text.splitlines():
        has_private_font_chars = bool(re.search(r"[\uf000-\uf8ff]", line))
        has_replacement_noise = line.count("�") + line.count("\x00") > 3
        if has_private_font_chars or has_replacement_noise or looks_like_legacy_hindi_font_text(line):
            dropped += 1
            continue
        cleaned_line = strip_legacy_noise_lines(strip_private_font_chars(line))
        if cleaned_line:
            kept_lines.append(cleaned_line)
    return normalize_text("\n".join(kept_lines)), dropped


def load_outputs() -> tuple[list[PdfRecord], list[WebPageRecord]]:
    records: list[PdfRecord] = []
    page_records: list[WebPageRecord] = []
    with OUTPUT_JSONL.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("record_type") == "webpage_text":
                page_records.append(WebPageRecord(**item))
            else:
                records.append(PdfRecord(**item))
    return records, page_records


def main() -> None:
    records, page_records = load_outputs()
    original_meta = json.loads(OUTPUT_META.read_text(encoding="utf-8")) if OUTPUT_META.exists() else {}
    meta = dict(original_meta)
    failed = meta.get("failed", [])
    failed_pages = meta.get("failed_pages", [])

    cleaned_pages: list[WebPageRecord] = []
    dropped_page_lines = 0
    for page_record in page_records:
        cleaned_text, dropped = clean_webpage_text(page_record.text)
        dropped_page_lines += dropped
        if not cleaned_text:
            continue
        page_record.text = cleaned_text
        page_record.char_count = len(cleaned_text)
        page_record.text_sha256 = text_hash(cleaned_text)
        cleaned_pages.append(page_record)

    cleaned_records: list[PdfRecord] = []
    dropped_pages = 0
    dropped_records = 0
    for record in records:
        cleaned_text, dropped = clean_pdf_text(record.text)
        dropped_pages += dropped
        if not cleaned_text:
            dropped_records += 1
            continue
        record.text = cleaned_text
        record.char_count = len(cleaned_text)
        record.text_sha256 = text_hash(cleaned_text)
        record.pages_extracted = max(0, record.pages_extracted - dropped)
        record.extracted_at_utc = datetime.now(timezone.utc).isoformat()
        cleaned_records.append(record)

    write_outputs(cleaned_records, cleaned_pages, failed, failed_pages)
    meta = json.loads(OUTPUT_META.read_text(encoding="utf-8"))
    for key in ("seed_page_count", "seed_pages"):
        if key in original_meta:
            meta[key] = original_meta[key]
    meta["legacy_hindi_cleanup"] = {
        "cleaned_at_utc": datetime.now(timezone.utc).isoformat(),
        "dropped_pages": dropped_pages,
        "dropped_webpage_lines": dropped_page_lines,
        "dropped_records": dropped_records,
    }
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Cleaned legacy Hindi pages: dropped_pages={dropped_pages}, "
        f"dropped_webpage_lines={dropped_page_lines}, "
        f"dropped_records={dropped_records}, records={len(cleaned_records)}"
    )


if __name__ == "__main__":
    main()
