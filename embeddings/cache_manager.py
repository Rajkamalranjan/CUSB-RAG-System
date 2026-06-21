"""Small file-backed embedding cache helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class EmbeddingCache:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = {}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def key(model_name: str, text: str) -> str:
        return hashlib.md5(f"{model_name}\0{text}".encode("utf-8", errors="ignore")).hexdigest()

    def get(self, model_name: str, text: str) -> list[float] | None:
        return self.data.get(self.key(model_name, text))

    def set(self, model_name: str, text: str, vector: list[float]) -> None:
        self.data[self.key(model_name, text)] = vector

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data), encoding="utf-8")

