"""Run retrieval and generation evaluation."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    python = sys.executable
    subprocess.run([python, "src/research_eval.py", "--split", "test"], check=True)
    subprocess.run([python, "src/6_llm_as_judge.py", "--limit", "50"], check=False)
    subprocess.run([python, "evaluation/ragas_benchmark.py", "--limit", "50"], check=False)


if __name__ == "__main__":
    main()
