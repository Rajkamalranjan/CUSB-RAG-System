"""Production API router for CUSB RAG."""

from __future__ import annotations

import time
import os
from typing import Any

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.core.pipeline import ProductionRAGPipeline
from backend.middleware.auth import create_access_token, require_admin, verify_admin_password
from backend.middleware.prompt_guard import is_safe_query
from backend.middleware.rate_limiter import rate_limit
from backend.middleware.scope_guard import scope_refusal_answer
from backend.utils.analytics import analytics_summary, log_chat_event
from backend.utils.metrics import CHAT_LATENCY, CHAT_REQUESTS, UPLOAD_REQUESTS, metrics_text


router = APIRouter()
pipeline: ProductionRAGPipeline | None = None


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=512)
    filters: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    confidence: float
    not_found: bool


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=1, max_length=256)


class DeleteDocumentRequest(BaseModel):
    source_file: str = Field(..., min_length=1, max_length=500)


@router.on_event("startup")
def load_pipeline() -> None:
    global pipeline
    pipeline = ProductionRAGPipeline()


@router.post("/auth/login")
def login(request: LoginRequest) -> dict[str, Any]:
    if request.username != "admin" or not verify_admin_password(request.password):
        return {"ok": False, "error": "Invalid credentials"}
    return {
        "ok": True,
        "access_token": create_access_token(subject=request.username, role="admin"),
        "token_type": "bearer",
        "role": "admin",
    }


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limit(20, 60))])
def chat(request: ChatRequest) -> ChatResponse:
    assert pipeline is not None
    started = time.perf_counter()
    if not is_safe_query(request.query):
        CHAT_REQUESTS.labels(status="blocked").inc()
        return ChatResponse(
            answer=scope_refusal_answer(request.query),
            sources=[],
            confidence=0.0,
            not_found=True,
        )
    result = pipeline.answer(request.query, filters=request.filters)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    CHAT_LATENCY.observe(elapsed_ms / 1000)
    CHAT_REQUESTS.labels(status="not_found" if result.not_found else "ok").inc()
    log_chat_event(
        {
            "query": request.query,
            "filters": request.filters,
            "source_count": len(result.sources),
            "confidence": result.confidence,
            "not_found": result.not_found,
            "latency_ms": elapsed_ms,
        }
    )
    return ChatResponse(**result.__dict__)


@router.websocket("/ws/chat")
async def chat_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    assert pipeline is not None
    try:
        payload = await websocket.receive_json()
        request = ChatRequest(**payload)
        result = chat(request)
        for token in result.answer.split():
            await websocket.send_json({"type": "token", "text": token + " "})
        await websocket.send_json({"type": "sources", "sources": result.sources})
        await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json({"type": "error", "error": str(exc)})
    finally:
        await websocket.close()


@router.get("/search", dependencies=[Depends(rate_limit(30, 60))])
def search(query: str, top_k: int = 10) -> dict[str, Any]:
    assert pipeline is not None
    chunks = pipeline.retriever.retrieve(query, top_k=top_k)
    return {"query": query, "results": chunks}


@router.post("/upload", dependencies=[Depends(rate_limit(5, 60))])
async def upload_pdf(file: UploadFile = File(...), _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload.pdf").name
    if not safe_name.lower().endswith(".pdf"):
        return {"status": "rejected", "error": "Only PDF uploads are accepted."}
    target = upload_dir / safe_name
    target.write_bytes(await file.read())
    try:
        from backend.tasks import ingest_uploaded_pdf

        task = ingest_uploaded_pdf.delay(str(target))
        UPLOAD_REQUESTS.labels(status="queued").inc()
        return {"status": "queued", "task_id": task.id, "file": str(target)}
    except Exception as exc:
        from ingestion.loaders.incremental_indexer import index_pdf_incremental

        result = index_pdf_incremental(target)
        UPLOAD_REQUESTS.labels(status="saved_not_queued").inc()
        return {
            "status": "indexed_without_celery",
            "file": str(target),
            "celery_error": str(exc),
            "result": result,
        }


@router.post("/reindex")
def reindex_placeholder(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    try:
        from backend.tasks import reindex_all

        task = reindex_all.delay()
        return {"status": "queued", "task_id": task.id}
    except Exception as exc:
        return {
            "status": "not_queued",
            "error": str(exc),
            "next_step": "Start Redis/Celery or run scripts/ingest_all.py manually.",
        }


@router.post("/index/qdrant")
def index_qdrant_endpoint(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    try:
        from backend.tasks import index_qdrant

        task = index_qdrant.delay()
        return {"status": "queued", "task_id": task.id}
    except Exception as exc:
        return {
            "status": "not_queued",
            "error": str(exc),
            "next_step": "Start Qdrant/Redis/Celery or run scripts/index_qdrant.py manually.",
        }


@router.post("/documents/delete")
def delete_document_endpoint(
    request: DeleteDocumentRequest,
    _admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    from ingestion.loaders.incremental_indexer import delete_document

    return delete_document(request.source_file)


@router.get("/documents")
def documents(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    manifest = Path("data/index_manifest.json")
    if not manifest.exists():
        return {"documents": {}}
    import json

    return json.loads(manifest.read_text(encoding="utf-8"))


@router.post("/feedback")
def feedback(payload: dict[str, Any]) -> dict[str, Any]:
    log_chat_event({"feedback": payload})
    return {"status": "recorded", "payload": payload}


@router.get("/health")
def health() -> dict[str, Any]:
    gpu = {"available": False}
    try:
        import torch

        gpu = {
            "available": bool(torch.cuda.is_available()),
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
    except Exception as exc:
        gpu = {"available": False, "error": str(exc).splitlines()[0]}
    return {
        "status": "ok",
        "pipeline_loaded": pipeline is not None,
        "retriever": type(pipeline.retriever).__name__ if pipeline else None,
        "gpu": gpu,
    }


@router.get("/admin/status")
def admin_status(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    assert pipeline is not None
    retriever = pipeline.retriever
    dense = getattr(retriever, "dense", retriever)
    chunks = getattr(dense, "chunks", None)
    vector_count = None
    index = getattr(dense, "index", None)
    if index is not None:
        vector_count = getattr(index, "ntotal", None)
    manifest = Path("data/index_manifest.json")
    log_path = Path("reports/chat_logs.jsonl")
    return {
        "pipeline_loaded": pipeline is not None,
        "retriever": type(retriever).__name__,
        "llm_provider": pipeline.provider_name,
        "fallback_llm_provider": os.getenv("FALLBACK_LLM_PROVIDER", ""),
        "chunk_count": len(chunks) if chunks is not None else None,
        "vector_count": vector_count,
        "manifest_exists": manifest.exists(),
        "logged_events": len(log_path.read_text(encoding="utf-8").splitlines()) if log_path.exists() else 0,
    }


@router.get("/analytics")
def analytics(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return analytics_summary()


@router.get("/metrics")
def metrics() -> Response:
    return Response(content=metrics_text(), media_type="text/plain; version=0.0.4")
