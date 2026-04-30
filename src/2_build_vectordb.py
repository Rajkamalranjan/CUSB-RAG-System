"""
Step 2: Build FAISS vector index from chunks.

Run AFTER 1_build_chunks.py.
Usage: python src/2_build_vectordb.py
"""

import json
import pickle
import sys

import numpy as np

from config import CHUNKS_PATH, EMBED_MODEL, EMBED_PATH, INDEX_PATH

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

META_PATH = EMBED_PATH.with_suffix(".meta.json")


def load_chunks(path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"❌  Chunks file not found: {path}\n"
            f"    Run Step 1 first: python src/1_build_chunks.py"
        )
    with open(path, "rb") as f:
        return pickle.load(f)


def cache_is_valid(chunks: list[dict]) -> bool:
    if not EMBED_PATH.exists() or not META_PATH.exists():
        return False

    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    return (
        meta.get("embedding_model") == EMBED_MODEL
        and meta.get("chunk_count") == len(chunks)
        and meta.get("text_char_total") == sum(len(c["text"]) for c in chunks)
    )


def save_cache_metadata(chunks: list[dict], embeddings: np.ndarray):
    meta = {
        "embedding_model": EMBED_MODEL,
        "chunk_count": len(chunks),
        "embedding_shape": list(embeddings.shape),
        "text_char_total": sum(len(c["text"]) for c in chunks),
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def build_embeddings(chunks: list[dict]) -> np.ndarray:
    """Encode all chunk texts into vectors."""
    from sentence_transformers import SentenceTransformer

    print(f"\n🤖  Loading embedding model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    texts = [c["text"] for c in chunks]
    print(f"🔄  Encoding {len(texts)} chunks...")

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.astype("float32")


def build_faiss_index(embeddings: np.ndarray):
    """Build a FAISS flat index using cosine similarity via inner product."""
    import faiss

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def main():
    print("=" * 60)
    print("🔧  STEP 2 — Building FAISS Vector Database")
    print("=" * 60)

    print(f"\n📦  Loading chunks: {CHUNKS_PATH}")
    chunks = load_chunks(CHUNKS_PATH)
    print(f"    ✅  {len(chunks)} chunks loaded")

    if cache_is_valid(chunks):
        print(f"\n📂  Found compatible cached embeddings: {EMBED_PATH}")
        embeddings = np.load(str(EMBED_PATH))
        print(f"    ✅  Shape: {embeddings.shape}")
    else:
        print("\nℹ️   No compatible embedding cache found; rebuilding embeddings.")
        embeddings = build_embeddings(chunks)
        np.save(str(EMBED_PATH), embeddings)
        save_cache_metadata(chunks, embeddings)
        print(f"\n💾  Embeddings saved to: {EMBED_PATH}")
        print(f"💾  Cache metadata saved to: {META_PATH}")

    print("\n⚡  Building FAISS index...")
    import faiss

    index = build_faiss_index(embeddings)
    print(f"    ✅  Index contains {index.ntotal} vectors (dim={index.d})")

    faiss.write_index(index, str(INDEX_PATH))
    print(f"\n💾  Index saved to: {INDEX_PATH}")

    print("\n🧪  Sanity test — searching for 'hostel fee kya hai'...")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBED_MODEL)
    q_vec = model.encode(["hostel fee kya hai"], normalize_embeddings=True).astype("float32")
    scores, indices = index.search(q_vec, k=3)
    print("    Top 3 matches:")
    for rank, (idx, score) in enumerate(zip(indices[0], scores[0]), 1):
        heading = chunks[idx]["heading"]
        print(f"      {rank}. [{score:.3f}] {heading}")

    print("\n✅  Done! Now run: python src/3_chatbot.py")


if __name__ == "__main__":
    main()
