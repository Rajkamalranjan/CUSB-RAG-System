"""Gemini provider adapter."""

from __future__ import annotations

import os


class GeminiProvider:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.api_key = os.getenv("GEMINI_API_KEY")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return "I could not find this in available CUSB data."
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(prompt)
        return getattr(response, "text", "").strip() or "I could not find this in available CUSB data."

