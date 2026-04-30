# CUSB RAG System - Research Documentation

## Table of Contents

1. [Research Overview](#research-overview)
2. [Experimental Setup](#experimental-setup)
3. [Evaluation Framework](#evaluation-framework)
4. [Running Research Experiments](#running-research-experiments)
5. [Results Analysis](#results-analysis)
6. [Research Quality Metrics](#research-quality-metrics)

---

## Research Overview

This project implements a **Research-Grade Retrieval-Augmented Generation (RAG) System** for Central University of South Bihar (CUSB). The system is designed to investigate:

- **Multilingual Information Retrieval**: Performance across English, Hindi, and Hinglish queries
- **RAG Architecture Effectiveness**: Component ablation and baseline comparisons
- **Evaluation Methodologies**: LLM-as-judge scoring vs traditional metrics
- **Performance Tradeoffs**: Context size, retrieval depth, and latency

### Key Research Contributions

1. **Multilingual RAG Framework**: Support for Indian languages with phonetic query expansion
2. **LLM-as-Judge Evaluation**: Automated scoring for faithfulness, correctness, and helpfulness
3. **Comprehensive Ablation Studies**: Systematic evaluation of components
4. **Statistical Analysis Framework**: Significance testing and effect size calculation

---

## Experimental Setup

### Environment Configuration

Create `.env` file with research-specific settings:

```env
# Core Configuration
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-2.5-flash-lite
EMBED_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# Retrieval Settings
TOP_K=5
MAX_CONTEXT=3000
RETRIEVAL_CANDIDATES=25
INCLUDE_QA_IN_INDEX=true

# Advanced Features
USE_RERANKER=true
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
ENABLE_QUERY_EXPANSION=true

# Research Settings
ENABLE_LLM_JUDGE=true
LLM_JUDGE_MODEL=gemini-2.5-flash
CROSS_VALIDATION_FOLDS=5
SIGNIFICANCE_THRESHOLD=0.05
ENABLE_HUMAN_ANNOTATION=false

# Logging
VERBOSE_LOGGING=true
SAVE_EXPERIMENT_LOGS=true
```

### Data Preparation

#### Step 1: Build Chunks
```powershell
venv\Scripts\python.exe src\1_build_chunks.py
```

Splits the markdown knowledge base into retrievable chunks. Creates:
- `cusb_chunks.pkl`: Serialized chunks
- `cusb_chunks_preview.json`: Human-readable preview
- `cusb_chunks_meta.json`: Chunk metadata

#### Step 2: Build Vector Database
```powershell
venv\Scripts\python.exe src\2_build_vectordb.py
```

Creates embeddings and FAISS index:
- `cusb_embeddings.npy`: Embedding vectors
- `cusb_vector.index`: FAISS index for retrieval

### Held-Out Test Set

For rigorous evaluation, create a held-out test set:

```powershell
# Build chunks WITHOUT QA pairs
venv\Scripts\python.exe src\1_build_chunks.py --exclude-qa
venv\Scripts\python.exe src\2_build_vectordb.py
```

---

## Evaluation Framework

### 1. Multilingual Benchmark (`5_benchmark_rag.py`)

Run the fixed benchmark suite across languages:

```powershell
# With LLM generation (full RAG)
venv\Scripts\python.exe src\5_benchmark_rag.py

# Retrieval-only (baseline)
venv\Scripts\python.exe src\5_benchmark_rag.py --no-llm
```

**Output**: `reports/rag_benchmark_YYYYMMDD_HHMMSS.jsonl`

**Metrics Captured**:
- Latency (milliseconds)
- Retrieved sources with similarity scores
- Generated answers
- Language detection accuracy

### 2. Retrieval Evaluation (`4_evaluate_retrieval.py`)

Evaluate retrieval quality on QA dataset:

```powershell
venv\Scripts\python.exe src\4_evaluate_retrieval.py --limit 100 --top-k 5
```

**Output**: `eval/retrieval_eval.jsonl`

**Evaluation Method**: Token overlap between retrieved context and reference answer

### 3. LLM-as-Judge Evaluation (`6_llm_as_judge.py`)

Comprehensive answer evaluation:

```powershell
# Evaluate latest benchmark
venv\Scripts\python.exe src\6_llm_as_judge.py

# Evaluate specific file
venv\Scripts\python.exe src\6_llm_as_judge.py --input reports/rag_benchmark_20260430_103231.jsonl
```

**Evaluation Dimensions**:

| Metric | Description | Scale |
|--------|-------------|-------|
| **Faithfulness** | Answer follows retrieved context | 1-5 |
| **Correctness** | Factual accuracy | 1-5 |
| **Helpfulness** | Addresses user query | 1-5 |
| **Completeness** | Covers important aspects | 1-5 |
| **Language Quality** | Grammar and clarity | 1-5 |

**Output**: `eval/llm_judge_YYYYMMDD_HHMMSS.jsonl`

### 4. Statistical Analysis (`7_statistical_analysis.py`)

Analyze and compare results with statistical rigor:

```powershell
# Analyze single results file
python src\7_statistical_analysis.py --analyze reports/rag_benchmark_20260430_103231.jsonl

# Compare two results files
python src\7_statistical_analysis.py --compare eval/llm_judge_1.jsonl eval/llm_judge_2.jsonl --metric overall_score
```

**Statistical Tests**:
- **Descriptive Statistics**: Mean, median, std dev, percentiles
- **Normality Testing**: Shapiro-Wilk test
- **Parametric Tests**: Independent t-test, ANOVA
- **Non-parametric Tests**: Mann-Whitney U, Spearman correlation
- **Effect Size**: Cohen's d
- **Confidence Intervals**: 95% CI for means

---

## Running Research Experiments

### Experiment 1: Baseline Comparison

Compare RAG against simpler approaches:

```powershell
venv\Scripts\python.exe src\9_baseline_comparison.py --queries 10
```

**Baselines**:
1. **LLM-Only**: Direct generation without retrieval
2. **Retrieval-Only**: Returned chunks as-is
3. **Full RAG**: Retrieval + generation

**Output**: `reports/baseline_comparison_YYYYMMDD_HHMMSS.jsonl`

### Experiment 2: Ablation Studies

#### 2a. Embedding Model Ablation

Compare different embedding models:

```powershell
venv\Scripts\python.exe src\8_ablation_studies.py --study embedding
```

**Models Tested**:
- `paraphrase-multilingual-MiniLM-L12-v2` (default)
- `all-MiniLM-L6-v2` (efficient)
- `all-mpnet-base-v2` (higher quality)
- `multilingual-e5-small` (E5 small)
- `multilingual-e5-large` (E5 large)

**Metrics**: Latency, retrieval quality, multilingual performance

#### 2b. Context Window Ablation

Test different context sizes:

```powershell
venv\Scripts\python.exe src\8_ablation_studies.py --study context
```

**Window Sizes Tested**: 1000, 2000, 3000, 4000, 5000 characters

**Metrics**: Latency, answer quality, context utilization

#### 2c. Top-K Ablation

Evaluate impact of retrieval depth:

```powershell
venv\Scripts\python.exe src\8_ablation_studies.py --study topk
```

**Top-K Values Tested**: 1, 3, 5, 10

**Metrics**: Quality improvement per chunk, diminishing returns

#### 2d. Run All Ablations

```powershell
venv\Scripts\python.exe src\8_ablation_studies.py --study all
```

**Output**: Multiple JSONL files in `reports/ablation_*.jsonl`

### Experiment 3: Advanced Features

Test query expansion and reranking:

```powershell
venv\Scripts\python.exe src\10_advanced_features.py
```

**Features Evaluated**:
- Query expansion for Hindi/Hinglish
- Cross-encoder reranking
- Semantic caching
- Hybrid retrieval (semantic + lexical)

---

## Results Analysis

### Quick Analysis Pipeline

```powershell
# 1. Run benchmark
python src\5_benchmark_rag.py

# 2. Evaluate with LLM judge
python src\6_llm_as_judge.py

# 3. Statistical analysis
python src\7_statistical_analysis.py --analyze eval/llm_judge_latest.jsonl
```

### Generate Research Report

Analyze all experiments:

```python
from pathlib import Path
from src.statistical_analysis import ResultsAnalyzer

analyzer = ResultsAnalyzer()

# Analyze benchmark results
benchmark_path = Path("reports/rag_benchmark_20260430_103231.jsonl")
analysis = analyzer.analyze_results(benchmark_path)

# Print key statistics
for metric, stats in analysis["metrics"].items():
    print(f"{metric}:")
    print(f"  Mean: {stats['mean']:.4f}")
    print(f"  95% CI: [{stats['confidence_interval'][0]:.4f}, {stats['confidence_interval'][1]:.4f}]")
```

### Comparison Analysis

```python
# Compare two RAG configurations
path1 = Path("reports/baseline_comparison.jsonl")
path2 = Path("reports/ablation_topk_results.jsonl")

comparison = analyzer.compare_results(path1, path2, metric="overall_score")

print(f"T-test p-value: {comparison['ttest']['p_value']:.4f}")
print(f"Cohen's d: {comparison['ttest']['cohens_d']:.4f}")
print(f"Significant: {comparison['ttest']['significant']}")
```

---

## Research Quality Metrics

### Evaluation Quality Indicators

| Aspect | Target | Status |
|--------|--------|--------|
| **Sample Size** | ≥100 queries | ✅ Configurable |
| **Held-Out Test Set** | Yes | ✅ Supported |
| **Statistical Significance** | α=0.05 | ✅ T-tests, ANOVA |
| **Effect Size Reporting** | Cohen's d | ✅ Calculated |
| **Multiple Metrics** | ≥3 dimensions | ✅ 5 LLM-judge dimensions |
| **Baseline Comparisons** | ≥2 baselines | ✅ LLM-only, retrieval-only |
| **Ablation Studies** | All components | ✅ Embedding, context, top-k |
| **Reproducibility** | Config documented | ✅ .env template + RESEARCH.md |
| **Error Analysis** | Documented | ✅ JSONL output format |

### Paper-Ready Output

**Results files** are automatically saved in JSONL format with:
- Full reproducibility information
- Metadata (timestamp, configuration, model versions)
- Per-example details and aggregated statistics
- LLM-judge scores for quality assessment

Example output structure:

```json
{
  "type": "metadata",
  "created_at_utc": "2026-04-30T10:35:36.434070+00:00",
  "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
  "gemini_model": "gemini-2.5-flash-lite",
  "top_k": 5
}
{
  "query": "What is CUSB?",
  "language": "English",
  "latency_ms": 26504.68,
  "answer": "...",
  "sources": [...],
  "judge_scores": {
    "faithfulness": 5,
    "correctness": 5,
    "helpfulness": 4,
    "completeness": 4,
    "language_quality": 5,
    "overall_score": 4.6
  }
}
```

---

## Research Scripts Quick Reference

| Script | Purpose | Command |
|--------|---------|---------|
| `1_build_chunks.py` | Create retrievable chunks | `python src\1_build_chunks.py` |
| `2_build_vectordb.py` | Build embeddings + index | `python src\2_build_vectordb.py` |
| `3_chatbot.py` | Interactive chatbot | `python src\3_chatbot.py` |
| `4_evaluate_retrieval.py` | Retrieval quality eval | `python src\4_evaluate_retrieval.py --limit 100` |
| `5_benchmark_rag.py` | Multilingual benchmark | `python src\5_benchmark_rag.py` |
| `6_llm_as_judge.py` | LLM-based evaluation | `python src\6_llm_as_judge.py` |
| `7_statistical_analysis.py` | Statistical testing | `python src\7_statistical_analysis.py --analyze` |
| `8_ablation_studies.py` | Component ablation | `python src\8_ablation_studies.py --study all` |
| `9_baseline_comparison.py` | Baseline comparison | `python src\9_baseline_comparison.py` |
| `10_advanced_features.py` | Advanced techniques | `python src\10_advanced_features.py` |

---

## Paper Structure Suggestion

### Proposed Paper Outline

```
1. Introduction
   - Problem: Multilingual QA for Indian universities
   - Approach: RAG with LLM-as-judge evaluation
   - Contributions: Multilingual framework, evaluation methodology

2. Related Work
   - RAG systems (Lewis et al., 2020)
   - LLM-as-judge evaluation
   - Multilingual embeddings

3. Methodology
   - System architecture (retrieval → ranking → generation)
   - Data preparation (CUSB knowledge base + QA pairs)
   - Evaluation framework (LLM-as-judge + statistical tests)

4. Experiments
   - 4.1 Baseline Comparison (RAG vs LLM-only vs retrieval-only)
   - 4.2 Ablation Studies (embedding models, context size, top-k)
   - 4.3 Multilingual Performance (English vs Hindi vs Hinglish)
   - 4.4 Advanced Features (reranking, query expansion)

5. Results
   - Performance metrics with confidence intervals
   - Statistical significance (p-values, effect sizes)
   - Error analysis and failure cases

6. Discussion
   - Key findings
   - Limitations
   - Future work

7. Conclusion
```

---

## Troubleshooting Research Setup

### Common Issues

**Issue**: Missing dependencies
```powershell
pip install -r requirements.txt
pip install scipy  # For statistical tests
```

**Issue**: API quota exceeded
```env
# Use fallback models
GEMINI_FALLBACK_MODELS=gemini-flash-lite-latest,gemini-2.5-flash,gemma-3-1b-it
```

**Issue**: OOM on large datasets
```powershell
# Use smaller top-k and batch size
python src\8_ablation_studies.py --study embedding  # Smaller test set
```

---

## Additional Resources

- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [Sentence-Transformers](https://www.sbert.net/)
- [Google Generative AI](https://ai.google.dev/)
- [Statistical Testing in Python](https://docs.scipy.org/doc/scipy/reference/stats.html)

---

**Last Updated**: April 30, 2026  
**Version**: 1.0
