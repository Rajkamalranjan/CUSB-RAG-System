"""Run the current CUSB ingestion pipeline end to end."""

from __future__ import annotations

import subprocess
import sys


STEPS = [
    ["src/merge_all_data.py"],
    ["src/1_build_chunks.py"],
    ["src/2_build_vectordb.py"],
    ["scripts/index_qdrant.py"],
]


def main() -> None:
    python = sys.executable
    for step in STEPS:
        print(f"Running: {python} {' '.join(step)}")
        subprocess.run([python, *step], check=True)


if __name__ == "__main__":
    main()
