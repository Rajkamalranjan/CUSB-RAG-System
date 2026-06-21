"""Heading-aware chunking wrapper around the current chunk builder."""

from __future__ import annotations

import sys
from pathlib import Path


def build_chunks() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    import importlib

    importlib.import_module("1_build_chunks").main()

