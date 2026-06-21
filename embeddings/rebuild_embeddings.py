"""Rebuild chunk embeddings and FAISS index with the selected embedding model."""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    model = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
    print(f"Rebuilding embeddings with: {model}")
    subprocess.run([sys.executable, "src/1_build_chunks.py"], check=True)
    subprocess.run([sys.executable, "src/2_build_vectordb.py"], check=True)


if __name__ == "__main__":
    main()

