"""Research-grade configuration for publishable CUSB EduRAG experiments.

This module is intentionally separate from config.py so experiment settings can
evolve without destabilizing the existing chatbot/API path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from config import BASE_DIR, DATA_DIR, EVAL_DIR, REPORTS_DIR


RESEARCH_DIR = BASE_DIR / "research"
BENCHMARK_DIR = DATA_DIR / "benchmark"


@dataclass(frozen=True)
class ResearchExperimentConfig:
    """Single source of truth for IEEE/PhD-level experiments."""

    project_name: str = "CUSB-EduRAG"
    random_seed: int = int(os.getenv("RESEARCH_RANDOM_SEED", "42"))
    train_ratio: float = float(os.getenv("RESEARCH_TRAIN_RATIO", "0.70"))
    validation_ratio: float = float(os.getenv("RESEARCH_VALIDATION_RATIO", "0.15"))
    test_ratio: float = float(os.getenv("RESEARCH_TEST_RATIO", "0.15"))
    dense_top_k: int = int(os.getenv("DENSE_TOP_K", "40"))
    bm25_top_k: int = int(os.getenv("BM25_TOP_K", "40"))
    final_top_k: int = int(os.getenv("FINAL_TOP_K", "5"))
    rrf_k: int = int(os.getenv("RRF_K", "60"))
    factual_overlap_threshold: float = float(os.getenv("FACTUAL_OVERLAP_THRESHOLD", "0.50"))

    # RTX 4070 Super friendly local-model defaults.
    local_llm_model: str = os.getenv("LOCAL_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    local_embedding_model: str = os.getenv("LOCAL_EMBED_MODEL", "BAAI/bge-m3")
    local_reranker_model: str = os.getenv("LOCAL_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")


CONFIG = ResearchExperimentConfig()


def ensure_research_dirs() -> None:
    """Create experiment output directories."""
    for path in (RESEARCH_DIR, BENCHMARK_DIR, EVAL_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def benchmark_path(split: str) -> Path:
    return BENCHMARK_DIR / f"cusb_{split}.jsonl"


def report_path(name: str) -> Path:
    return REPORTS_DIR / name
