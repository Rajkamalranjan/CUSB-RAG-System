"""Merge textual data sources into one final corpus.

The script reads useful text-like data from data/ and data/benchmark/:
- Markdown files
- JSONL records
- JSON datasets/metadata

It skips binary/generated cache files such as PDF cache, FAISS indexes,
embeddings, pickle chunks, and backups. Outputs are written as:
- data/final_merged_corpus.md
- data/final_merged_corpus.jsonl
- data/final_merged_corpus_meta.json
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

OUTPUT_MD = DATA_DIR / "final_merged_corpus.md"
OUTPUT_JSONL = DATA_DIR / "final_merged_corpus.jsonl"
OUTPUT_META = DATA_DIR / "final_merged_corpus_meta.json"

TEXT_EXTENSIONS = {".md", ".txt", ".json", ".jsonl"}
SKIP_DIRS = {"backups", "pdf_cache"}
SKIP_NAMES = {
    OUTPUT_MD.name,
    OUTPUT_JSONL.name,
    OUTPUT_META.name,
}


def normalize_text(text: str) -> str:
    """Normalize text for stable hashing and cleaner output."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def content_hash(text: str) -> str:
    normalized = normalize_text(text).lower()
    return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()


def should_include(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return False
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    relative_parts = set(path.relative_to(DATA_DIR).parts[:-1])
    return not bool(relative_parts & SKIP_DIRS)


def safe_title(value: str, fallback: str) -> str:
    value = normalize_text(value)
    if not value:
        return fallback
    return value[:160]


def record_from_markdown(path: Path) -> list[dict[str, Any]]:
    text = normalize_text(path.read_text(encoding="utf-8", errors="ignore"))
    if not text:
        return []

    first_heading = next(
        (
            line.lstrip("#").strip()
            for line in text.splitlines()
            if line.strip().startswith("#")
        ),
        path.stem,
    )
    return [
        {
            "source_file": str(path.relative_to(BASE_DIR)),
            "record_type": "markdown_document",
            "title": safe_title(first_heading, path.stem),
            "text": text,
        }
    ]


def qa_record(item: dict[str, Any], path: Path, index: int) -> dict[str, Any] | None:
    question = item.get("input") or item.get("question")
    answer = item.get("output") or item.get("reference_answer") or item.get("answer")
    if not question and not answer:
        return None

    question = normalize_text(str(question or ""))
    answer = normalize_text(str(answer or ""))
    text = f"Q: {question}\nA: {answer}".strip()
    return {
        "source_file": str(path.relative_to(BASE_DIR)),
        "record_type": "qa_pair",
        "title": safe_title(question, f"QA {index + 1}"),
        "text": text,
        "data": item,
    }


def generic_json_record(item: Any, path: Path, index: int) -> dict[str, Any]:
    if isinstance(item, dict):
        title = (
            item.get("title")
            or item.get("heading")
            or item.get("id")
            or item.get("url")
            or f"{path.stem} record {index + 1}"
        )
    else:
        title = f"{path.stem} record {index + 1}"

    text = json.dumps(item, ensure_ascii=False, indent=2)
    return {
        "source_file": str(path.relative_to(BASE_DIR)),
        "record_type": "json_record",
        "title": safe_title(str(title), f"{path.stem} record {index + 1}"),
        "text": normalize_text(text),
        "data": item,
    }


def records_from_json(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        text = normalize_text(path.read_text(encoding="utf-8", errors="ignore"))
        return [
            {
                "source_file": str(path.relative_to(BASE_DIR)),
                "record_type": "raw_json_text",
                "title": path.stem,
                "text": text,
            }
        ] if text else []

    items = data if isinstance(data, list) else [data]
    records = []
    for index, item in enumerate(items):
        if isinstance(item, dict):
            qa = qa_record(item, path, index)
            if qa:
                records.append(qa)
                continue
        records.append(generic_json_record(item, path, index))
    return records


def records_from_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for index, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            records.append(
                {
                    "source_file": str(path.relative_to(BASE_DIR)),
                    "record_type": "jsonl_text_line",
                    "title": f"{path.stem} line {index + 1}",
                    "text": line,
                }
            )
            continue

        if isinstance(item, dict):
            qa = qa_record(item, path, index)
            records.append(qa if qa else generic_json_record(item, path, index))
        else:
            records.append(generic_json_record(item, path, index))
    return records


def load_records(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return record_from_markdown(path)
    if suffix == ".json":
        return records_from_json(path)
    if suffix == ".jsonl":
        return records_from_jsonl(path)
    return []


def discover_sources() -> list[Path]:
    def source_priority(path: Path) -> tuple[int, int, str]:
        relative = path.relative_to(DATA_DIR)
        is_nested = len(relative.parts) > 1
        is_benchmark = relative.parts[0] == "benchmark"
        if path.name == "final_data_set.json":
            group = 0
        elif not is_nested:
            group = 1
        elif is_benchmark:
            group = 2
        else:
            group = 3
        return (group, len(relative.parts), str(relative).lower())

    return sorted(
        (path for path in DATA_DIR.rglob("*") if path.is_file() and should_include(path)),
        key=source_priority,
    )


def write_outputs(records: list[dict[str, Any]], sources: list[Path], skipped_duplicates: int) -> None:
    md_parts = [
        "# CUSB Final Merged Corpus\n\n",
        f"Created at UTC: {datetime.now(timezone.utc).isoformat()}\n\n",
        f"Total source files included: {len(sources)}\n\n",
        f"Total unique records: {len(records)}\n\n",
        "Skipped folders: `data/backups`, `data/pdf_cache`\n\n",
        "Skipped binary/generated extensions: `.pkl`, `.npy`, `.index`, `.pdf`\n\n",
        "---\n\n",
    ]

    for index, record in enumerate(records, start=1):
        md_parts.append(f"## {index}. {record['title']}\n\n")
        md_parts.append(f"**Source:** `{record['source_file']}`\n\n")
        md_parts.append(f"**Type:** `{record['record_type']}`\n\n")
        md_parts.append(record["text"])
        md_parts.append("\n\n---\n\n")

    OUTPUT_MD.write_text("".join(md_parts), encoding="utf-8")

    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for index, record in enumerate(records, start=1):
            row = {
                "id": f"merged_{index:06d}",
                **record,
                "char_count": len(record["text"]),
                "content_hash": content_hash(record["text"]),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    by_type: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for record in records:
        by_type[record["record_type"]] = by_type.get(record["record_type"], 0) + 1
        by_source[record["source_file"]] = by_source.get(record["source_file"], 0) + 1

    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file_count": len(sources),
        "record_count": len(records),
        "skipped_duplicate_records": skipped_duplicates,
        "total_text_chars": sum(len(record["text"]) for record in records),
        "outputs": {
            "markdown": str(OUTPUT_MD.relative_to(BASE_DIR)),
            "jsonl": str(OUTPUT_JSONL.relative_to(BASE_DIR)),
            "metadata": str(OUTPUT_META.relative_to(BASE_DIR)),
        },
        "included_sources": [str(path.relative_to(BASE_DIR)) for path in sources],
        "record_type_counts": by_type,
        "records_by_source": by_source,
        "skipped_dirs": sorted(SKIP_DIRS),
        "skipped_extensions": [".pkl", ".npy", ".index", ".pdf"],
    }
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    print("=" * 70)
    print("CUSB DATA MERGE")
    print("=" * 70)

    sources = discover_sources()
    print(f"Discovered {len(sources)} text source files")

    records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    skipped_duplicates = 0

    for path in sources:
        loaded = load_records(path)
        kept = 0
        for record in loaded:
            text = normalize_text(record.get("text", ""))
            if not text:
                continue
            record["text"] = text
            digest = content_hash(text)
            if digest in seen_hashes:
                skipped_duplicates += 1
                continue
            seen_hashes.add(digest)
            records.append(record)
            kept += 1
        print(f"  {path.relative_to(BASE_DIR)} -> {kept} records")

    write_outputs(records, sources, skipped_duplicates)

    print("\nMerge complete")
    print(f"  Unique records: {len(records)}")
    print(f"  Duplicate records skipped: {skipped_duplicates}")
    print(f"  Markdown: {OUTPUT_MD}")
    print(f"  JSONL:    {OUTPUT_JSONL}")
    print(f"  Metadata: {OUTPUT_META}")


if __name__ == "__main__":
    main()
