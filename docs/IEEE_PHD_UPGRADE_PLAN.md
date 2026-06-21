# CUSB-EduRAG IEEE/PhD Upgrade Plan

## Research Position

The publishable contribution should be framed as:

**CUSB-EduRAG: A production-grade multilingual and code-mixed retrieval-augmented generation framework for Indian higher-education student support.**

Do not position the work as only a chatbot. The research contribution is the combination of:

- English, Hindi, and Hinglish/code-mixed university QA.
- Leakage-free benchmark design.
- Hybrid dense + lexical retrieval with Reciprocal Rank Fusion.
- Optional cross-encoder reranking.
- Grounded generation with abstention.
- Human and automatic evaluation.
- Local deployment and experimentation on affordable hardware such as an RTX 4070 Super.

## Gap To Target

Recent 2025-2026 RAG literature still leaves room for:

- Multilingual educational RAG for low-resource and code-mixed settings.
- Transparent comparisons between dense, lexical, hybrid, reranked, and LLM-only systems.
- Leakage-aware benchmark construction.
- Human evaluation alongside automated metrics.
- Production reporting: latency, memory, cost, monitoring, and failure analysis.

## Required Experiments

Minimum paper-ready systems:

1. LLM-only baseline.
2. BM25-only retrieval.
3. Dense FAISS retrieval.
4. Dense + BM25 + RRF hybrid retrieval.
5. Hybrid + cross-encoder reranking.
6. Hybrid + local RTX 4070 Super LLM.
7. Hybrid + API LLM.

Minimum metrics:

- Recall@k.
- MRR.
- nDCG@k.
- Factual token recall.
- Faithfulness.
- Answer relevance.
- Abstention accuracy for unanswerable questions.
- Latency mean, median, p95.
- GPU memory usage for local models.
- Cost per 1,000 queries for API models.

## Dataset Protocol

Use `src/create_benchmark_splits.py` to generate:

- `data/benchmark/cusb_train.jsonl`
- `data/benchmark/cusb_validation.jsonl`
- `data/benchmark/cusb_test.jsonl`
- `data/benchmark/cusb_unanswerable.jsonl`

For formal claims, rebuild the vector index without held-out QA rows. The current project includes QA chunks in the index, which is useful for chatbot behavior but optimistic for research.

## RTX 4070 Super Track

Recommended local stack:

- Embedding model: `BAAI/bge-m3`
- Reranker: `BAAI/bge-reranker-v2-m3`
- Local LLM: `Qwen/Qwen2.5-7B-Instruct` or `meta-llama/Llama-3.1-8B-Instruct`
- Fine-tuning: Unsloth QLoRA, 4-bit, LoRA rank 16 or 32
- Inference: vLLM, llama.cpp, or Transformers with bitsandbytes

Start with retrieval and reranking before fine-tuning. Fine-tuning should be a later ablation, not the foundation of the paper.

## Production Requirements

Before claiming production-grade:

- Fix all mojibake/encoding corruption in Hindi and symbol text.
- Add local production settings and service scripts.
- Validate all required environment variables at startup.
- Add structured JSON logs.
- Add API rate limiting and request IDs.
- Store feedback and query traces.
- Add tests for retrieval, language detection, and API responses.
- Add monitoring for latency, error rate, and fallback rate.

## IEEE Paper Skeleton

1. Abstract
2. Introduction
3. Related Work
4. Research Gap
5. Dataset Construction
6. CUSB-EduRAG Architecture
7. Retrieval Methods
8. Generation and Grounding
9. Experimental Setup
10. Results
11. Ablation Studies
12. Human Evaluation
13. Production Deployment Analysis
14. Threats to Validity
15. Conclusion

## Immediate Command Path

```powershell
python src\create_benchmark_splits.py
python src\research_eval.py --split test --limit 25
python src\research_eval.py --split unanswerable
```

The first reports are diagnostic. For publication-grade results, rebuild the index with QA held out, then run the full evaluation.
