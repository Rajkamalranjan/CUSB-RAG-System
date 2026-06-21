"""Ollama provider adapter."""

from __future__ import annotations

import os

import requests


class OllamaProvider:
    def __init__(self, model_name: str | None = None, url: str | None = None):
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3.1")
        self.url = url or os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

    def generate(self, prompt: str) -> str:
        response = requests.post(self.url, json={"model": self.model_name, "prompt": prompt, "stream": False}, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()

