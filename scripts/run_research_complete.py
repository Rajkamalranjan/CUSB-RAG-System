"""Run no-Docker research pipeline steps that are safe to repeat."""

from __future__ import annotations

import subprocess
import sys


STEPS = [
    ["training/data/generate_synthetic_pairs.py", "--limit", "500"],
    ["evaluation/formal_metrics.py", "--limit", "200"],
    ["evaluation/ragas_benchmark.py", "--limit", "50"],
]


def main() -> None:
    for step in STEPS:
        print(f"Running: {sys.executable} {' '.join(step)}")
        subprocess.run([sys.executable, *step], check=False)


if __name__ == "__main__":
    main()
