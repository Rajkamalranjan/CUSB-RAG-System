# Research Experiment Quick-Start Guide

Get your CUSB RAG research pipeline running in 5 minutes!

## Prerequisites

```powershell
# Setup Python environment
py -3.13 -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Initial Setup (One Time)

```powershell
# 1. Create .env file with your API key
# (See RESEARCH.md for template)

# 2. Build data pipeline
venv\Scripts\python.exe src\1_build_chunks.py
venv\Scripts\python.exe src\2_build_vectordb.py
```

## Quick Research Pipeline (5 min)

```powershell
# 1. Run multilingual benchmark (2 min)
venv\Scripts\python.exe src\5_benchmark_rag.py

# 2. Evaluate answers with LLM-as-judge (2 min)
venv\Scripts\python.exe src\6_llm_as_judge.py

# 3. Analyze results statistically (1 min)
python src\7_statistical_analysis.py --analyze reports/llm_judge_latest.jsonl
```

## Comprehensive Research Experiments (30 min)

```powershell
# 1. Baseline Comparisons (10 min)
venv\Scripts\python.exe src\9_baseline_comparison.py --queries 10

# 2. Ablation Studies (15 min)
venv\Scripts\python.exe src\8_ablation_studies.py --study all

# 3. Advanced Features
venv\Scripts\python.exe src\10_advanced_features.py

# 4. Analyze everything
python src\7_statistical_analysis.py --analyze reports/rag_benchmark_*.jsonl
python src\7_statistical_analysis.py --compare reports/baseline_comparison.jsonl reports/ablation_*.jsonl
```

## Output Files

All results go to:
- `reports/` - Benchmark and comparison results
- `eval/` - Detailed evaluation results
- `annotations/` - Human annotation (if enabled)

## Key Scripts

| Goal | Command |
|------|---------|
| Quick test | `python src\5_benchmark_rag.py` |
| Full evaluation | `python src\6_llm_as_judge.py` |
| Statistics | `python src\7_statistical_analysis.py --analyze reports/*.jsonl` |
| Baselines | `python src\9_baseline_comparison.py` |
| Ablations | `python src\8_ablation_studies.py --study all` |

## For Your Research Paper

1. **Results**: See `reports/rag_benchmark_*.jsonl` (with judge scores)
2. **Statistics**: Run analysis with `7_statistical_analysis.py`
3. **Methodology**: See `RESEARCH.md` for detailed evaluation framework
4. **Reproducibility**: All configs in `.env` + timestamped JSONL outputs

---

**See `RESEARCH.md` for comprehensive documentation!**
