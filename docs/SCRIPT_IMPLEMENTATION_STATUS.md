# CUSB RAG Script Implementation Status

This document tracks how much of the target "PhD-level production RAG" script is active in this repository.

Current deployment direction: **local no-Docker runtime**. Docker Compose,
Dockerfiles, and Nginx container config were removed; local PowerShell scripts
now start indexing, backend, Celery worker, and frontend.

## Implemented in main runtime

- CUSB-specific RAG chatbot over local CUSB corpus.
- Multilingual English/Hindi/Hinglish query support.
- FAISS dense retrieval over `data/cusb_chunks.pkl`.
- BM25 sparse retrieval integrated into the main `src/rag_engine.py` runtime.
- Optional Qdrant runtime backend via `VECTOR_BACKEND=qdrant`.
- Qdrant indexing loader can reuse `data/cusb_embeddings.npy` and upsert in batches.
- Local Qdrant storage is indexed via `QDRANT_PATH=data\qdrant_local`; Windows backend startup defaults to FAISS to avoid embedded-Qdrant file locks.
- Hybrid score fusion using dense score, BM25 bonus, RRF-style rank bonus, lexical bonus, and domain quality rules.
- Groq/Gemini LLM generation with grounded prompt rules.
- Hallucination controls for programme, syllabus, fee, and URL answers.
- CLI `/sources` display with source file, URL/page when available, and BM25 score.
- Final 50-question retrieval smoke test:
  - Input: `eval/final_50_questions.jsonl`
  - Runner: `scripts/run_final_retrieval_eval.py`
  - Output: `reports/final_retrieval_eval_*.jsonl`

## Present but partial

- Qdrant wrapper exists in `vectorstore/qdrant_client.py`; runtime selection is available, and local no-Docker indexing uses `data\qdrant_local`.
- Production hybrid wrapper exists in `retriever/hybrid/hybrid_search.py`, but the CLI currently uses the integrated hybrid path in `src/rag_engine.py`.
- BGE reranker wrapper exists in `reranker/bge_reranker.py`, but GPU FP16 latency has not been benchmarked.
- FastAPI production router exists under `backend/`, but the simpler `src/api_server.py` is also present.
- FastAPI now includes JWT admin login, admin-protected upload/reindex/index/analytics, per-IP rate limiting, Prometheus metrics, WebSocket token streaming, and GPU-aware health output.
- Next.js frontend includes chat, filters, source panel, citation verification status, chat history, admin login, upload, reindex, Qdrant indexing, and analytics controls.
- Incremental PDF indexing exists in `ingestion/loaders/incremental_indexer.py`; uploads can be embedded and upserted into local Qdrant without Docker.
- Document delete API exists at `/api/documents/delete` for source-file based removal from local chunk metadata and Qdrant.
- Citation verification exists in `llm/prompts/citation_verifier.py` and attaches grounding status to response sources.
- Synthetic training data generation now adds BM25 hard-negative chunk IDs.
- Formal metrics runner exists in `evaluation/formal_metrics.py` for Hit@1, Hit@5, MRR@10, latency, and hallucination-rate style reporting.
- Docker has been intentionally removed from the implementation target.
- RAGAS benchmark scaffold exists in `evaluation/ragas_benchmark.py`, but it does not yet run full `ragas.evaluate()`.
- Self-supervised training script exists in `training/train.py`, but synthetic query generation and golden validation are not complete.

## Missing for full script-level claim

- Incremental Qdrant indexing with document change detection.
- Fine-tuned `intfloat/multilingual-e5-small` model trained on reviewed CUSB synthetic pairs.
- BGE reranker in FP16 with measured P50/P95 latency.
- 200-query golden benchmark with labels and final metrics: Hit@K, MRR, Recall@K, faithfulness, hallucination rate.
- Page-level citation verification for every generated answer sentence.
- Recomputing FAISS after source-file deletion if you switch back to FAISS runtime.
- Grafana dashboards.
- Full polished admin analytics charts.

## Next implementation order

1. Validate FastAPI and Next.js locally with `scripts/start_backend.ps1` and `scripts/start_frontend.ps1`.
2. Run `python scripts/run_research_complete.py`.
3. Train the fine-tuned retriever with reviewed synthetic pairs.
4. Build/review a 200-query golden benchmark and publish final metrics.
5. Add Grafana-style chart UI for analytics if needed.
