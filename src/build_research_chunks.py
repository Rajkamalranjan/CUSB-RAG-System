"""Build RAG chunks from the cleaned CUSB research corpus.

This script converts data/cusb_research_corpus.jsonl into the chunk format used
by the existing FAISS builder. By default it backs up the current chunk files,
then writes:

    data/cusb_chunks.pkl
    data/cusb_chunks_preview.json
    data/cusb_chunks_meta.json

Use this after:
    python src/scrape_cusb_research.py --max-pages 100 --delay 1
    python src/build_research_corpus.py

Then run:
    python src/2_build_vectordb.py
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import CHUNKS_JSON_PATH, CHUNKS_META_PATH, CHUNKS_PATH, DATA_DIR

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_CORPUS = DATA_DIR / "cusb_research_corpus.jsonl"
DEFAULT_PDF_CORPUS = DATA_DIR / "cusb_research_pdf_corpus.jsonl"
BACKUP_DIR = DATA_DIR / "backups"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    text = normalize_whitespace(text)
    if len(text) <= max_chars:
        return [text] if text else []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            current = f"{tail}\n\n{paragraph}".strip() if tail else paragraph
        else:
            for start in range(0, len(paragraph), max_chars - overlap):
                part = paragraph[start : start + max_chars].strip()
                if part:
                    chunks.append(part)
            current = ""

    if current:
        chunks.append(current)

    return chunks


def format_chunk_text(record: dict, body: str) -> str:
    pdf_lines = []
    for item in record.get("pdf_links", [])[:20]:
        label = item.get("text") or item.get("url")
        pdf_lines.append(f"- {label}: {item.get('url')}")

    header = [
        f"Title: {record.get('title', 'Untitled')}",
        f"Category: {record.get('category', 'general')}",
        f"Source URL: {record.get('url', '')}",
    ]
    if pdf_lines:
        header.append("PDF Links:\n" + "\n".join(pdf_lines))

    return "\n".join(header) + "\n\n" + body


def normalize_records(records: list[dict], source_type: str) -> list[dict]:
    normalized = []
    for record in records:
        item = dict(record)
        item["source_type"] = source_type
        if source_type == "pdf":
            item["title"] = item.get("title") or "Untitled PDF"
            item["url"] = item.get("url") or item.get("parent_url")
            item["pdf_links"] = []
        normalized.append(item)
    return normalized


def build_chunks(records: list[dict], max_chars: int, overlap: int) -> list[dict]:
    chunks = []
    chunk_id = 0

    for record in records:
        parts = split_text(record.get("text", ""), max_chars=max_chars, overlap=overlap)
        for part_index, part in enumerate(parts, 1):
            heading = record.get("title", "Untitled")
            if len(parts) > 1:
                heading = f"{heading} (Part {part_index})"

            chunk_text = format_chunk_text(record, part)
            chunks.append(
                {
                    "id": chunk_id,
                    "heading": heading,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "source_url": record.get("url"),
                    "source_type": record.get("source_type", "web"),
                    "category": record.get("category"),
                    "record_id": record.get("id"),
                }
            )
            chunk_id += 1

    return chunks


def backup_existing_outputs() -> list[str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backed_up = []

    for path in (CHUNKS_PATH, CHUNKS_JSON_PATH, CHUNKS_META_PATH):
        if path.exists():
            backup_path = BACKUP_DIR / f"{path.stem}_{timestamp}{path.suffix}"
            shutil.copy2(path, backup_path)
            backed_up.append(str(backup_path))

    return backed_up


def save_chunks(chunks: list[dict], meta: dict) -> None:
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    preview = [
        {
            "id": chunk["id"],
            "heading": chunk["heading"],
            "category": chunk.get("category"),
            "source_url": chunk.get("source_url"),
            "preview": chunk["text"][:300],
        }
        for chunk in chunks[:50]
    ]
    with open(CHUNKS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(preview, f, ensure_ascii=False, indent=2)

    with open(CHUNKS_META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_CORPUS))
    parser.add_argument("--pdf-input", default=str(DEFAULT_PDF_CORPUS))
    parser.add_argument("--include-pdfs", action="store_true", default=True)
    parser.add_argument("--no-pdfs", dest="include_pdfs", action="store_false")
    parser.add_argument("--max-chars", type=int, default=1800)
    parser.add_argument("--overlap", type=int, default=180)
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Missing research corpus: {input_path}. Run python src/build_research_corpus.py first."
        )

    web_records = normalize_records(load_jsonl(input_path), "web")
    pdf_path = Path(args.pdf_input)
    pdf_records = []
    if args.include_pdfs and pdf_path.exists():
        pdf_records = normalize_records(load_jsonl(pdf_path), "pdf")

    records = web_records + pdf_records
    backed_up = [] if args.no_backup else backup_existing_outputs()
    chunks = build_chunks(records, max_chars=args.max_chars, overlap=args.overlap)

    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "builder": "build_research_chunks.py",
        "corpus_path": str(input_path),
        "pdf_corpus_path": str(pdf_path) if pdf_records else "",
        "web_record_count": len(web_records),
        "pdf_record_count": len(pdf_records),
        "record_count": len(records),
        "total_chunks": len(chunks),
        "min_chars": min((chunk["char_count"] for chunk in chunks), default=0),
        "max_chars": max((chunk["char_count"] for chunk in chunks), default=0),
        "avg_chars": sum(chunk["char_count"] for chunk in chunks) // max(1, len(chunks)),
        "max_source_chars": args.max_chars,
        "overlap": args.overlap,
        "include_qa_in_index": False,
        "source": "cleaned_cusb_research_corpus",
        "backups": backed_up,
    }

    save_chunks(chunks, meta)

    print("Research chunks built")
    print(f"  Records : {len(records)}")
    print(f"  Chunks  : {len(chunks)}")
    print(f"  Saved   : {CHUNKS_PATH}")
    print(f"  Preview : {CHUNKS_JSON_PATH}")
    print(f"  Meta    : {CHUNKS_META_PATH}")
    if backed_up:
        print("  Backups :")
        for path in backed_up:
            print(f"    - {path}")


if __name__ == "__main__":
    main()
