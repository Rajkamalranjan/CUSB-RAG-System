"""Index current CUSB chunks into Qdrant."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import os

os.environ.setdefault("QDRANT_PATH", str(ROOT / "data" / "qdrant_local"))

from ingestion.loaders.qdrant_loader import load_chunks_to_qdrant


def main() -> None:
    if os.getenv("QDRANT_PATH"):
        print(f"Using local Qdrant storage: {os.getenv('QDRANT_PATH')}")
    load_chunks_to_qdrant()
    print("Qdrant indexing complete.")


if __name__ == "__main__":
    main()
