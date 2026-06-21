"""Structured PDF extraction with OCR fallback hook."""

from __future__ import annotations

from pathlib import Path

import fitz


def extract_pdf_text(path: Path) -> list[dict]:
    doc = fitz.open(path)
    pages = []
    for index, page in enumerate(doc, 1):
        text = page.get_text("text").strip()
        pages.append({"page": index, "text": text, "source_file": str(path)})
    return pages

