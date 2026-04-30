"""
Step 1: Build text chunks from CUSB_markdown.md for RAG.

Run this FIRST before building the vector database.
Usage: python src/1_build_chunks.py
"""

import json
import pickle
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import (
    CHUNKS_JSON_PATH,
    CHUNKS_META_PATH,
    CHUNKS_PATH,
    INCLUDE_QA_IN_INDEX,
    MARKDOWN_PATH,
    QA_DATASET_PATH,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_markdown(path: Path) -> str:
    """Read the markdown file."""
    if not path.exists():
        raise FileNotFoundError(
            f"❌  Markdown file not found: {path}\n"
            f"    Place CUSB_markdown.md inside the data/ folder."
        )
    return path.read_text(encoding="utf-8")


def split_by_headings(md_text: str) -> list[dict]:
    """
    Split markdown into chunks at every ## or ### heading.
    Each chunk = {id, heading, text, char_count}
    """
    pattern = re.compile(r"(?=^#{2,3} )", re.MULTILINE)
    raw_sections = pattern.split(md_text)

    chunks = []
    for idx, section in enumerate(raw_sections):
        section = section.strip()
        if not section:
            continue

        lines = section.splitlines()
        heading = lines[0].lstrip("#").strip() if lines else f"Section {idx}"
        body = re.sub(r"\n{3,}", "\n\n", section)

        chunks.append(
            {
                "id": idx,
                "heading": heading,
                "text": body,
                "char_count": len(body),
            }
        )

    return chunks


def add_qa_chunks(chunks: list[dict], json_path: Path, chunk_size: int = 5) -> list[dict]:
    """Add QA-pair chunks from final_data_set.json as fallback knowledge."""
    if not json_path.exists():
        print(f"⚠️  QA dataset not found at {json_path}, skipping QA chunks.")
        return chunks

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    qa_pairs = [
        {"q": item["input"].strip(), "a": item["output"].strip()}
        for item in data
        if item.get("input") and item.get("output")
    ]

    start_id = len(chunks)
    for i in range(0, len(qa_pairs), chunk_size):
        batch = qa_pairs[i : i + chunk_size]
        text = "\n\n".join(f"Q: {pair['q']}\nA: {pair['a']}" for pair in batch)
        chunks.append(
            {
                "id": start_id + i // chunk_size,
                "heading": f"QA Batch {i // chunk_size + 1}",
                "text": text,
                "char_count": len(text),
            }
        )

    return chunks


def save_chunks(chunks: list[dict], pkl_path: Path, json_path: Path):
    pkl_path.parent.mkdir(parents=True, exist_ok=True)

    with open(pkl_path, "wb") as f:
        pickle.dump(chunks, f)

    preview = [
        {"id": chunk["id"], "heading": chunk["heading"], "preview": chunk["text"][:200]}
        for chunk in chunks[:20]
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(preview, f, ensure_ascii=False, indent=2)


def save_metadata(chunks: list[dict], include_qa: bool):
    markdown_chunks = [chunk for chunk in chunks if not chunk["heading"].startswith("QA Batch")]
    qa_chunks = [chunk for chunk in chunks if chunk["heading"].startswith("QA Batch")]
    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "include_qa_in_index": include_qa,
        "total_chunks": len(chunks),
        "markdown_chunks": len(markdown_chunks),
        "qa_chunks": len(qa_chunks),
        "min_chars": min(chunk["char_count"] for chunk in chunks),
        "max_chars": max(chunk["char_count"] for chunk in chunks),
        "avg_chars": sum(chunk["char_count"] for chunk in chunks) // len(chunks),
        "markdown_path": str(MARKDOWN_PATH),
        "qa_dataset_path": str(QA_DATASET_PATH),
    }
    with open(CHUNKS_META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def main():
    include_qa = INCLUDE_QA_IN_INDEX and "--exclude-qa" not in sys.argv

    print("=" * 60)
    print("🔧  STEP 1 — Building chunks from Markdown")
    print("=" * 60)

    print(f"\n📖  Reading: {MARKDOWN_PATH}")
    md_text = load_markdown(MARKDOWN_PATH)
    print(f"    ✅  {len(md_text):,} characters loaded")

    chunks = split_by_headings(md_text)
    print(f"    ✅  {len(chunks)} heading-based chunks created")

    if include_qa:
        chunks = add_qa_chunks(chunks, QA_DATASET_PATH, chunk_size=5)
    else:
        print("    ℹ️  QA chunks excluded from index for held-out style evaluation")
    print(f"    ✅  Total chunks after adding QA pairs: {len(chunks)}")

    sizes = [chunk["char_count"] for chunk in chunks]
    print(f"\n📊  Chunk stats:")
    print(f"    Min size : {min(sizes):,} chars")
    print(f"    Max size : {max(sizes):,} chars")
    print(f"    Avg size : {sum(sizes) // len(sizes):,} chars")

    save_chunks(chunks, CHUNKS_PATH, CHUNKS_JSON_PATH)
    save_metadata(chunks, include_qa)
    print(f"\n💾  Saved:")
    print(f"    → {CHUNKS_PATH}   (pickle, used by vectordb builder)")
    print(f"    → {CHUNKS_JSON_PATH}  (JSON preview)")
    print(f"    → {CHUNKS_META_PATH}  (build metadata)")

    print("\n🔍  First 3 chunks preview:")
    print("-" * 60)
    for chunk in chunks[:3]:
        print(f"  [{chunk['id']}] {chunk['heading']}")
        print(f"      {chunk['text'][:120].replace(chr(10), ' ')}...")
    print("-" * 60)
    print("\n✅  Done! Now run: python src/2_build_vectordb.py")


if __name__ == "__main__":
    main()
