"""Generation faithfulness benchmark entrypoint."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


if __name__ == "__main__":
    module = importlib.import_module("6_llm_as_judge")
    module.main()
