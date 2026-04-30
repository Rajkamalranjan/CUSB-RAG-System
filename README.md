# CUSB AI Chatbot: Research-Oriented RAG System

Retrieval-Augmented Generation chatbot for Central University of South Bihar
(CUSB). The project builds a local FAISS vector database from a Markdown
knowledge base and QA dataset, then answers student queries using Gemini.

## Project Structure

```text
data/
  CUSB_markdown.md             Knowledge base
  final_data_set.json          QA dataset
  cusb_chunks_preview.json     Human-readable chunk preview
src/
  1_build_chunks.py            Build retrievable chunks
  2_build_vectordb.py          Build embeddings and FAISS index
  3_chatbot.py                 Run CLI chatbot
  4_evaluate_retrieval.py      Retrieval evaluation harness
  5_benchmark_rag.py           Multilingual RAG benchmark runner
  6_llm_as_judge.py            LLM-based answer evaluation [NEW]
  7_statistical_analysis.py    Statistical testing and analysis [NEW]
  8_ablation_studies.py        Component ablation studies [NEW]
  9_baseline_comparison.py     Baseline comparisons [NEW]
  10_advanced_features.py      Advanced RAG techniques [NEW]
  config.py                    Shared experiment configuration
  rag_engine.py                RAG core engine
eval/
  retrieval_eval.jsonl         Evaluation results
reports/
  rag_benchmark_*.jsonl        Benchmark results
  baseline_comparison_*.jsonl  Baseline comparison results
  ablation_*.jsonl             Ablation study results
RESEARCH.md                    Comprehensive research guide [NEW]
QUICKSTART_RESEARCH.md         Quick reference for research [NEW]
RESEARCH_MODULES_INDEX.py      Module documentation [NEW]
requirements.txt
README.md
```

## Setup

```powershell
py -3.13 -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create `.env` in the project root:

```env
GEMINI_API_KEY=your_real_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_FALLBACK_MODELS=gemini-flash-lite-latest,gemini-2.5-flash,gemma-3-1b-it
EMBED_MODEL=paraphrase-multilingual-MiniLM-L12-v2
TOP_K=5
MAX_CONTEXT=3000
RETRIEVAL_CANDIDATES=25
INCLUDE_QA_IN_INDEX=true
USE_RERANKER=false
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

## Run Pipeline

```powershell
venv\Scripts\python.exe src\1_build_chunks.py
venv\Scripts\python.exe src\2_build_vectordb.py
venv\Scripts\python.exe src\3_chatbot.py
```

The chatbot answers in the same language style as the user query:

- English query -> English answer
- Hindi query in Devanagari -> Hindi answer
- Hinglish query -> Hinglish answer

Offline fallback mode:

```powershell
venv\Scripts\python.exe src\3_chatbot.py --no-llm
```

For held-out style retrieval experiments, rebuild chunks without inserting the
QA dataset into the vector database:

```powershell
venv\Scripts\python.exe src\1_build_chunks.py --exclude-qa
venv\Scripts\python.exe src\2_build_vectordb.py
```

## Evaluation

Run retrieval evaluation on the QA dataset:

```powershell
venv\Scripts\python.exe src\4_evaluate_retrieval.py --limit 100 --top-k 5
```

Run a fixed multilingual benchmark suite and save answers, latency, and sources:

```powershell
venv\Scripts\python.exe src\5_benchmark_rag.py --no-llm
```

The script writes per-example results to:

```text
eval/retrieval_eval.jsonl
reports/rag_benchmark_*.jsonl
```

Current evaluation is retrieval-focused. It estimates whether retrieved context
contains important tokens from the reference answer. For a stronger research
paper, add human annotation or LLM-as-judge scoring for faithfulness,
correctness, and answer helpfulness.

Important limitation: the QA dataset is also added into the retrieval corpus, so
retrieval scores can be optimistic. For a formal research report, create a
held-out test set that is not inserted into the vector database.

## Research-Level Features Added

- Configurable model names and retrieval settings through `.env`
- Automatic Gemini fallback models when one model hits quota
- Source-labeled context sent to the LLM
- Source metadata returned with each answer
- Graceful fallback when Gemini fails
- Retrieval evaluation harness with JSONL experiment logs
- Multilingual benchmark runner with latency and source logs
- Multilingual embedding model for English, Hindi, and Hinglish retrieval
- Optional held-out chunk build with `--exclude-qa`
- Optional cross-encoder reranker controlled by `.env`
- Windows UTF-8 console handling for Hindi/Hinglish output

## How RAG Works

1. Markdown and QA data are converted into chunks.
2. Chunks are embedded with `sentence-transformers`.
3. FAISS retrieves the most relevant chunks for a user query.
4. Retrieved context is passed to Gemini.
5. The answer is generated only from retrieved CUSB context.

---

## Research-Grade Evaluation & Analysis

This project includes comprehensive tools for research publication:

### 📊 LLM-as-Judge Evaluation (`6_llm_as_judge.py`)

Evaluate answers across multiple quality dimensions:

```powershell
venv\Scripts\python.exe src\6_llm_as_judge.py
```

Metrics evaluated:
- **Faithfulness**: Answer follows retrieved context (1-5)
- **Correctness**: Factual accuracy (1-5)
- **Helpfulness**: Addresses user query (1-5)
- **Completeness**: Covers important aspects (1-5)
- **Language Quality**: Grammar and fluency (1-5)

### 📈 Statistical Analysis (`7_statistical_analysis.py`)

Rigorous statistical testing for research papers:

```powershell
# Analyze results
python src\7_statistical_analysis.py --analyze eval/llm_judge_results.jsonl

# Compare configurations
python src\7_statistical_analysis.py --compare results1.jsonl results2.jsonl
```

Tests provided:
- Descriptive statistics (mean, median, std dev, percentiles, 95% CI)
- Hypothesis testing (t-tests, Mann-Whitney U, ANOVA)
- Effect size (Cohen's d)
- Significance testing (α=0.05)

### 🔬 Ablation Studies (`8_ablation_studies.py`)

Systematic evaluation of system components:

```powershell
# Embedding model ablation
python src\8_ablation_studies.py --study embedding

# Context window ablation
python src\8_ablation_studies.py --study context

# Top-K ablation
python src\8_ablation_studies.py --study topk

# All ablations
python src\8_ablation_studies.py --study all
```

### 📊 Baseline Comparison (`9_baseline_comparison.py`)

Compare against meaningful baselines:

```powershell
python src\9_baseline_comparison.py --queries 10
```

Baselines:
1. LLM-only (no retrieval)
2. Retrieval-only (no generation)
3. Full RAG (retrieval + generation)

### 🚀 Advanced Features (`10_advanced_features.py`)

Implement and test advanced RAG techniques:

```powershell
python src\10_advanced_features.py
```

Features:
- Query expansion for multilingual terms
- Cross-encoder reranking
- Semantic caching
- Hybrid retrieval (semantic + lexical)

### 📚 Complete Research Documentation

See [`RESEARCH.md`](RESEARCH.md) for:
- Detailed methodology
- Experimental protocols
- Evaluation frameworks
- Paper-ready output formats
- Statistical analysis examples

Quick start: [`QUICKSTART_RESEARCH.md`](QUICKSTART_RESEARCH.md)

Module index: [`RESEARCH_MODULES_INDEX.py`](RESEARCH_MODULES_INDEX.py)

---

## Research Quality Features

✅ **Data**: Held-out test set support, multilingual evaluation  
✅ **Evaluation**: 5-dimensional LLM-as-judge scoring  
✅ **Statistics**: Hypothesis testing, effect sizes, confidence intervals  
✅ **Baselines**: Multiple comparison baselines  
✅ **Ablations**: Systematic component analysis  
✅ **Reproducibility**: Timestamped JSONL outputs with full metadata  
✅ **Documentation**: Complete methodology and protocol documentation  

---

## Project Updates (Research Edition)

**New modules for research:**
- `6_llm_as_judge.py` - LLM-based answer evaluation
- `7_statistical_analysis.py` - Statistical testing and analysis
- `8_ablation_studies.py` - Component ablation studies
- `9_baseline_comparison.py` - Baseline comparisons
- `10_advanced_features.py` - Advanced RAG techniques

**Enhanced config:**
- Alternative embedding models
- Research parameters (ENABLE_LLM_JUDGE, significance thresholds)
- Ablation configurations

**New documentation:**
- `RESEARCH.md` - Full research guide
- `QUICKSTART_RESEARCH.md` - Quick reference
- `RESEARCH_MODULES_INDEX.py` - Module documentation
