"""Optional LangChain backend for the CUSB RAG system.

This module keeps the existing custom retriever/vector database intact and only
uses LangChain for prompt formatting and LLM calls. It is useful for experiments
without replacing the main RAGPipeline in rag_engine.py.

Usage:
    python src/langchain_rag.py
    python src/langchain_rag.py --provider groq
    python src/langchain_rag.py --provider gemini
    python src/langchain_rag.py --no-llm
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402
    CHATBOT_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    LLM_PROVIDER,
    TOP_K,
)
from rag_engine import (  # noqa: E402
    FallbackGenerator,
    Retriever,
    SYSTEM_PROMPT,
    detect_query_language,
)


class LangChainGenerator:
    """Generate answers through LangChain chat model integrations."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or os.getenv("LANGCHAIN_LLM_PROVIDER") or LLM_PROVIDER).lower()
        self.model_name = model or os.getenv("LANGCHAIN_MODEL")

        try:
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError as exc:
            raise ImportError(
                "LangChain packages are not installed. Run:\n"
                "  python -m pip install langchain-core "
                "langchain-google-genai langchain-groq"
            ) from exc

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "user",
                    "=== CONTEXT (from CUSB knowledge base) ===\n"
                    "{context}\n"
                    "===========================================\n\n"
                    "User Question: {query}\n"
                    "Required Output Language: {output_language}\n\n"
                    "Answer:",
                ),
            ]
        )
        self.output_parser = StrOutputParser()
        self.llm = self._build_llm()
        self.chain = self.prompt | self.llm | self.output_parser

    def _build_llm(self):
        if self.provider == "groq":
            from langchain_groq import ChatGroq

            api_key = GROQ_API_KEY or os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY is required for LangChain Groq backend.")
            self.model_name = self.model_name or CHATBOT_MODEL
            return ChatGroq(
                model=self.model_name,
                groq_api_key=api_key,
                temperature=0.3,
                max_tokens=1024,
            )

        if self.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is required for LangChain Gemini backend.")
            self.model_name = self.model_name or GEMINI_MODEL
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=api_key,
                temperature=0.3,
            )

        raise ValueError("Unsupported LangChain provider. Use 'gemini' or 'groq'.")

    def generate(self, query: str, context: str, output_language: str = "English") -> str:
        return self.chain.invoke(
            {
                "query": query,
                "context": context,
                "output_language": output_language,
            }
        ).strip()


class LangChainRAGPipeline:
    """RAG pipeline with custom retrieval and optional LangChain generation."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        use_llm: bool = True,
    ):
        self.retriever = Retriever()
        self.fallback_generator = FallbackGenerator()

        if not use_llm:
            self.generator = self.fallback_generator
            print("Running LangChain RAG in retrieval-only fallback mode.")
            return

        try:
            self.generator = LangChainGenerator(provider=provider, model=model)
            print(
                "LangChain LLM connected "
                f"({self.generator.provider}: {self.generator.model_name})"
            )
        except Exception as exc:
            print(f"LangChain LLM unavailable: {exc}")
            print("Using offline fallback generator.")
            self.generator = self.fallback_generator

    def answer(self, query: str, top_k: int = TOP_K, verbose: bool = False) -> dict:
        output_language = detect_query_language(query)
        chunks = self.retriever.retrieve(query, top_k=top_k)
        context = self.retriever.build_context(chunks)

        if verbose:
            print(f"\nRetrieved {len(chunks)} chunks:")
            for chunk in chunks:
                print(f"   [{chunk['score']:.3f}] {chunk['heading']}")

        try:
            answer = self.generator.generate(query, context, output_language=output_language)
        except Exception as exc:
            fallback = self.fallback_generator.generate(
                query,
                context,
                output_language=output_language,
            )
            answer = f"{exc}\n\nUsing offline fallback:\n\n{fallback}"

        answer = self._clean_answer(answer)

        return {
            "answer": answer,
            "language": output_language,
            "sources": [
                {
                    "id": chunk.get("id"),
                    "heading": chunk["heading"],
                    "score": chunk["score"],
                    "char_count": chunk.get("char_count"),
                }
                for chunk in chunks
            ],
            "context": context,
        }

    def search(self, query: str, k: int = TOP_K) -> list[dict]:
        return self.retriever.retrieve(query, top_k=k)

    @staticmethod
    def _clean_answer(answer: str) -> str:
        cleaned_lines = []
        for line in answer.splitlines():
            stripped = line.strip()
            if stripped.startswith(("Source:", "Sources:", "The most relevant source")):
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run optional LangChain CUSB RAG chatbot.")
    parser.add_argument("--provider", choices=["gemini", "groq"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    rag = LangChainRAGPipeline(
        provider=args.provider,
        model=args.model,
        use_llm=not args.no_llm,
    )

    print("\nLangChain RAG ready. Type /quit to exit.\n")
    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not query:
            continue
        if query.lower() in {"/quit", "/exit", "quit", "exit"}:
            print("Goodbye.")
            break

        result = rag.answer(query, top_k=args.top_k, verbose=args.verbose)
        print("\nCUSB Bot:")
        print(result["answer"])
        print()


if __name__ == "__main__":
    main()
