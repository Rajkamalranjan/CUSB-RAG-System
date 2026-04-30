"""Shared configuration for the CUSB RAG system."""

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
EVAL_DIR = BASE_DIR / "eval"
REPORTS_DIR = BASE_DIR / "reports"

MARKDOWN_PATH = DATA_DIR / "CUSB_markdown.md"
QA_DATASET_PATH = DATA_DIR / "final_data_set.json"
CHUNKS_PATH = DATA_DIR / "cusb_chunks.pkl"
CHUNKS_JSON_PATH = DATA_DIR / "cusb_chunks_preview.json"
CHUNKS_META_PATH = DATA_DIR / "cusb_chunks_meta.json"
INDEX_PATH = DATA_DIR / "cusb_vector.index"
EMBED_PATH = DATA_DIR / "cusb_embeddings.npy"

EMBED_MODEL = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# Groq API configuration (free, fast alternative)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# LLM provider: "gemini" or "groq"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-flash-lite-latest,gemini-2.5-flash,gemma-3-1b-it",
    ).split(",")
    if model.strip()
]
TOP_K = int(os.getenv("TOP_K", "5"))
MAX_CONTEXT = int(os.getenv("MAX_CONTEXT", "3000"))
RETRIEVAL_CANDIDATES = int(os.getenv("RETRIEVAL_CANDIDATES", "25"))
INCLUDE_QA_IN_INDEX = os.getenv("INCLUDE_QA_IN_INDEX", "true").lower() in {"1", "true", "yes"}
USE_RERANKER = os.getenv("USE_RERANKER", "false").lower() in {"1", "true", "yes"}
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

# ============================================================================
# RESEARCH-LEVEL CONFIGURATIONS
# ============================================================================

# Alternative embedding models for ablation studies
ALTERNATIVE_EMBEDDING_MODELS = [
    "all-MiniLM-L6-v2",
    "all-mpnet-base-v2",
    "intfloat/multilingual-e5-small",
    "intfloat/multilingual-e5-large",
]

# Cross-validation settings
CROSS_VALIDATION_FOLDS = int(os.getenv("CROSS_VALIDATION_FOLDS", "5"))

# Query expansion strategies
ENABLE_QUERY_EXPANSION = os.getenv("ENABLE_QUERY_EXPANSION", "true").lower() in {"1", "true", "yes"}

# Context window variations
CONTEXT_WINDOW_SIZES = [1000, 2000, 3000, 4000, 5000]

# Top-K variations
TOP_K_VALUES = [1, 3, 5, 10]

# LLM-as-judge configuration
LLM_JUDGE_MODEL = os.getenv("LLM_JUDGE_MODEL", "gemini-2.5-flash")
ENABLE_LLM_JUDGE = os.getenv("ENABLE_LLM_JUDGE", "true").lower() in {"1", "true", "yes"}

# Human annotation support
ENABLE_HUMAN_ANNOTATION = os.getenv("ENABLE_HUMAN_ANNOTATION", "false").lower() in {"1", "true", "yes"}
ANNOTATION_DIR = BASE_DIR / "annotations"

# Statistical significance threshold
SIGNIFICANCE_THRESHOLD = float(os.getenv("SIGNIFICANCE_THRESHOLD", "0.05"))

# Logging configuration
VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "true").lower() in {"1", "true", "yes"}
SAVE_EXPERIMENT_LOGS = os.getenv("SAVE_EXPERIMENT_LOGS", "true").lower() in {"1", "true", "yes"}

# Ensure directories exist
ANNOTATION_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
