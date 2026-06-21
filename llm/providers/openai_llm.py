"""OpenAI provider adapter."""

from __future__ import annotations

import os


class OpenAIProvider:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def generate(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI()
        response = client.responses.create(model=self.model_name, input=prompt)
        return response.output_text.strip()

