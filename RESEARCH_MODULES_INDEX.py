"""
CUSB RAG Research System - Complete Module Index

This file documents all research-level modules and their usage.
"""

# ============================================================================
# RESEARCH MODULES ADDED
# ============================================================================

"""
NEW MODULE STRUCTURE:

src/
├── config.py (ENHANCED)
│   └── Added: Research configurations, alternative models, ablation settings
├── rag_engine.py (EXISTING)
│   └── Core RAG pipeline
├── 1_build_chunks.py (EXISTING)
├── 2_build_vectordb.py (EXISTING)
├── 3_chatbot.py (EXISTING)
├── 4_evaluate_retrieval.py (EXISTING)
├── 5_benchmark_rag.py (EXISTING)
│   └── Multilingual benchmark suite
├── 6_llm_as_judge.py (NEW - Research Evaluation)
│   └── LLM-based answer evaluation (faithfulness, correctness, helpfulness)
├── 7_statistical_analysis.py (NEW - Research Statistics)
│   └── Statistical testing, significance, effect size, confidence intervals
├── 8_ablation_studies.py (NEW - Research Experiments)
│   └── Component ablation (embedding, context, top-k)
├── 9_baseline_comparison.py (NEW - Research Baselines)
│   └── LLM-only vs Retrieval-only vs Full RAG comparison
├── 10_advanced_features.py (NEW - Advanced Techniques)
│   └── Query expansion, reranking, caching, hybrid retrieval

Documentation:
├── RESEARCH.md (NEW - Comprehensive guide)
│   └── Full research methodology and experimental protocols
├── QUICKSTART_RESEARCH.md (NEW - Quick reference)
│   └── 5-minute setup and experiment running
└── README.md (EXISTING)
    └── Project overview
"""

# ============================================================================
# MODULE: 6_llm_as_judge.py
# ============================================================================

"""
LLM-AS-JUDGE EVALUATION FRAMEWORK

Purpose: Evaluate RAG answers using LLM to score 5 dimensions

Evaluation Dimensions:
  1. Faithfulness (1-5): Answer follows retrieved context
  2. Correctness (1-5): Factual accuracy
  3. Helpfulness (1-5): Addresses user query
  4. Completeness (1-5): Covers important aspects
  5. Language Quality (1-5): Grammar and clarity

Usage:
  # Evaluate latest benchmark
  python src/6_llm_as_judge.py
  
  # Evaluate specific file
  python src/6_llm_as_judge.py --input reports/rag_benchmark_20260430_103231.jsonl
  
  # Save to custom path
  python src/6_llm_as_judge.py --output eval/my_evaluation.jsonl

Output:
  - JSONL file with per-example judge scores
  - Aggregate statistics (mean, min, max, std for each metric)
  
Example Output:
{
  "query": "What is CUSB?",
  "answer": "Central University of South Bihar...",
  "judge_scores": {
    "faithfulness": 5,
    "correctness": 5,
    "helpfulness": 4,
    "completeness": 4,
    "language_quality": 5,
    "overall_score": 4.6,
    "strengths": "Accurate and well-sourced",
    "weaknesses": "Could include more details"
  }
}
"""

# ============================================================================
# MODULE: 7_statistical_analysis.py
# ============================================================================

"""
STATISTICAL ANALYSIS FRAMEWORK

Purpose: Rigorous statistical analysis for research publication

Statistics Provided:
  - Descriptive: mean, median, std dev, min, max, percentiles
  - Normality: Shapiro-Wilk test
  - Parametric: t-tests, ANOVA
  - Non-parametric: Mann-Whitney U, Spearman correlation
  - Effect Size: Cohen's d
  - Confidence Intervals: 95% CI for means

Usage:
  # Analyze single file
  python src/7_statistical_analysis.py --analyze reports/rag_benchmark.jsonl
  
  # Compare two files
  python src/7_statistical_analysis.py --compare file1.jsonl file2.jsonl --metric overall_score
  
  # Compare different metrics
  python src/7_statistical_analysis.py --compare baseline.jsonl optimized.jsonl --metric latency_ms

Output Format:
{
  "file": "reports/rag_benchmark.jsonl",
  "num_results": 10,
  "metrics": {
    "overall_score": {
      "count": 10,
      "mean": 4.23,
      "median": 4.5,
      "std": 0.45,
      "min": 3.0,
      "max": 5.0,
      "q1": 3.9,
      "q3": 4.6,
      "iqr": 0.7,
      "confidence_interval": [3.9, 4.6]
    }
  }
}

Comparison Output Includes:
  - Independent t-test results (t-statistic, p-value)
  - Mann-Whitney U test (for non-normal distributions)
  - Cohen's d effect size
  - Statistical significance (α=0.05)
"""

# ============================================================================
# MODULE: 8_ablation_studies.py
# ============================================================================

"""
ABLATION STUDIES FRAMEWORK

Purpose: Systematic evaluation of system components

Ablation Types:

1. EMBEDDING MODEL ABLATION
   Tests: Different sentence-transformer models
   Models Tested:
   - paraphrase-multilingual-MiniLM-L12-v2 (default)
   - all-MiniLM-L6-v2 (efficient)
   - all-mpnet-base-v2 (higher quality)
   - multilingual-e5-small (E5 variant)
   - multilingual-e5-large (E5 variant)
   
   Usage:
   python src/8_ablation_studies.py --study embedding
   
   Output: Latency and quality metrics per model

2. CONTEXT WINDOW ABLATION
   Tests: Different max context sizes (1K-5K chars)
   
   Usage:
   python src/8_ablation_studies.py --study context
   
   Output: Quality-vs-latency tradeoff analysis

3. TOP-K ABLATION
   Tests: Different retrieval depths (1, 3, 5, 10)
   
   Usage:
   python src/8_ablation_studies.py --study topk
   
   Output: Diminishing returns analysis

Run All Ablations:
  python src/8_ablation_studies.py --study all
"""

# ============================================================================
# MODULE: 9_baseline_comparison.py
# ============================================================================

"""
BASELINE COMPARISON FRAMEWORK

Purpose: Establish performance baselines for research context

Baselines Tested:

1. LLM-ONLY (No Retrieval)
   - Direct query to Gemini
   - No context from CUSB knowledge base
   - Baseline for "hallucination risk"
   
2. RETRIEVAL-ONLY (No Generation)
   - Return top-K chunks as-is
   - No LLM processing
   - Baseline for "bare retrieval"
   
3. FULL RAG (Retrieval + Generation)
   - Our complete system
   - Retrieved context + LLM generation
   - Show RAG value

Usage:
  python src/9_baseline_comparison.py --queries 10

Output Comparison:
  {
    "baselines": {
      "llm_only": {
        "avg_latency_ms": 5234.5,
        "results": [...]
      },
      "retrieval_only": {
        "avg_latency_ms": 1023.3,
        "results": [...]
      },
      "rag_full": {
        "avg_latency_ms": 17644.5,
        "results": [...]
      }
    }
  }
"""

# ============================================================================
# MODULE: 10_advanced_features.py
# ============================================================================

"""
ADVANCED RAG FEATURES

Purpose: Implement and test advanced retrieval & generation techniques

Features Included:

1. QUERY EXPANSION
   - Hindi term expansion (सीयूएसबी → CUSB Central University...)
   - Hinglish expansion (kya → what is)
   - Related query generation
   
   Purpose: Improve retrieval recall for language-specific terms
   
2. RERANKING (Cross-Encoder)
   - Second-stage ranking with cross-encoder
   - Improves precision after FAISS retrieval
   - Model: cross-encoder/ms-marco-MiniLM-L-6-v2
   
   Usage: Set USE_RERANKER=true in .env
   
3. SEMANTIC CACHING
   - Cache results for repeated queries
   - Reduces latency for common questions
   - Configurable cache size
   
4. HYBRID RETRIEVAL
   - Combine semantic (embeddings) + lexical (BM25) search
   - Better coverage than either alone
   - Configurable weighting

Usage:
  python src/10_advanced_features.py

Output: Feature effectiveness metrics
"""

# ============================================================================
# RESEARCH QUALITY FEATURES IMPLEMENTED
# ============================================================================

"""
✅ RESEARCH QUALITY CHECKLIST:

Data & Evaluation:
  ✅ Held-out test set support (--exclude-qa)
  ✅ Multilingual evaluation (English, Hindi, Hinglish)
  ✅ Multiple evaluation metrics (5 LLM-judge dimensions)
  ✅ Baseline comparisons (LLM-only, retrieval-only)
  ✅ Ablation studies (embedding, context, top-k)

Statistical Analysis:
  ✅ Descriptive statistics (mean, median, std, percentiles)
  ✅ Hypothesis testing (t-test, Mann-Whitney U, ANOVA)
  ✅ Effect size reporting (Cohen's d)
  ✅ Confidence intervals (95% CI)
  ✅ Significance testing (α=0.05)

Reproducibility:
  ✅ All configs documented in .env template
  ✅ Timestamped JSONL outputs
  ✅ Metadata in every result file
  ✅ Deterministic evaluation protocols
  ✅ Complete source retrieval logging

Error Analysis:
  ✅ Per-example result tracking
  ✅ Error categorization
  ✅ Failure case documentation
  ✅ Confidence intervals for reliability

Documentation:
  ✅ RESEARCH.md (methodology)
  ✅ QUICKSTART_RESEARCH.md (quick reference)
  ✅ Inline code documentation
  ✅ Usage examples
  ✅ Output format specifications
"""

# ============================================================================
# TYPICAL RESEARCH WORKFLOW
# ============================================================================

"""
RECOMMENDED RESEARCH PIPELINE:

1. DATA SETUP (Once)
   python src/1_build_chunks.py --exclude-qa  # Held-out test set
   python src/2_build_vectordb.py

2. BASELINE ESTABLISHMENT (Day 1)
   python src/9_baseline_comparison.py --queries 50
   python src/7_statistical_analysis.py --analyze reports/baseline_comparison.jsonl

3. MAIN EXPERIMENTS (Day 2-3)
   python src/5_benchmark_rag.py
   python src/6_llm_as_judge.py
   
4. ABLATION STUDIES (Day 4-5)
   python src/8_ablation_studies.py --study all
   
5. ADVANCED FEATURES (Day 6)
   python src/10_advanced_features.py

6. FINAL ANALYSIS (Day 7)
   python src/7_statistical_analysis.py --analyze eval/llm_judge_final.jsonl
   # Compare baseline vs optimized
   python src/7_statistical_analysis.py --compare reports/baseline.jsonl eval/llm_judge_final.jsonl

OUTPUT FOR PAPER:
  - Results with 95% confidence intervals
  - Statistical significance tests (p-values)
  - Effect sizes (Cohen's d)
  - Ablation analysis
  - Error analysis with examples
"""

# ============================================================================
# CONFIGURATION FOR RESEARCH
# ============================================================================

"""
KEY .env SETTINGS FOR RESEARCH:

# Core Evaluation
ENABLE_LLM_JUDGE=true
LLM_JUDGE_MODEL=gemini-2.5-flash

# Statistical Testing
SIGNIFICANCE_THRESHOLD=0.05
CROSS_VALIDATION_FOLDS=5

# Advanced Features
ENABLE_QUERY_EXPANSION=true
USE_RERANKER=true

# Logging & Reproducibility
VERBOSE_LOGGING=true
SAVE_EXPERIMENT_LOGS=true
INCLUDE_QA_IN_INDEX=false  # For held-out evaluation

# Retrieval Parameters
TOP_K=5
MAX_CONTEXT=3000
RETRIEVAL_CANDIDATES=25
"""

# ============================================================================
# PAPER-READY OUTPUT
# ============================================================================

"""
All JSONL output files are structured for easy conversion to paper tables:

Structure:
  1. Metadata line with configuration
  2. Result lines (one JSON object per line)
  3. Each result includes:
     - Query
     - Language detected
     - Latency
     - Generated answer
     - Retrieved sources (with scores)
     - LLM judge scores (when evaluated)

Python Script to Generate Paper Table:
  
  import json
  
  results = []
  with open("eval/llm_judge_final.jsonl") as f:
      for line in f:
          results.append(json.loads(line))
  
  # Skip metadata
  data = [r for r in results if "type" not in r]
  
  # Print table
  print("Query | Latency (ms) | Faithfulness | Correctness | Overall Score")
  print("-" * 70)
  for result in data:
      scores = result.get("judge_scores", {})
      print(f"{result['query'][:20]} | {result['latency_ms']:.0f} | "
            f"{scores.get('faithfulness', '-')} | "
            f"{scores.get('correctness', '-')} | "
            f"{scores.get('overall_score', '-'):.2f}")
"""

print(__doc__)
