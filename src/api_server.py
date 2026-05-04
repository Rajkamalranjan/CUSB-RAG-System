"""
FastAPI Production Server for CUSB AI Assistant
Research + Production Grade API
"""

import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field

from rag_engine import RAGPipeline as _RAGPipeline
from frontend import CHAT_HTML


# ==================== Pydantic Models ====================

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, description="User question")
    language: str = Field(default="auto", description="Language: en, hi, hinglish, auto")


class SourceItem(BaseModel):
    chunk_id: Optional[int] = None
    heading: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    language: str
    processing_time: float
    query_id: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    version: str
    chunks: int
    vectors: int
    timestamp: str


# ==================== App State ====================

app_state = {
    "rag": None,
    "query_count": 0,
    "total_time": 0.0,
    "history": []
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading RAG pipeline...")
    app_state["rag"] = _RAGPipeline()
    print("RAG pipeline ready!")
    yield
    print("Shutting down...")


app = FastAPI(
    title="CUSB AI Assistant API",
    description="Production RAG API for Central University of South Bihar",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Endpoints ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    return CHAT_HTML


@app.get("/api/health", response_model=HealthResponse)
async def health():
    rag = app_state["rag"]
    chunks = len(rag.retriever.chunks) if rag else 0
    vectors = rag.retriever.index.ntotal if rag else 0
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        chunks=chunks,
        vectors=vectors,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    rag = app_state["rag"]
    if not rag:
        raise HTTPException(status_code=503, detail="RAG pipeline not loaded")

    start = time.time()
    query_id = uuid.uuid4().hex[:8]

    try:
        result = rag.answer(req.question)
        elapsed = time.time() - start

        sources = [
            SourceItem(
                chunk_id=s.get("id"),
                heading=s.get("heading", "Unknown")[:100],
                score=s.get("score", 0.0),
            )
            for s in result.get("sources", [])
        ]

        # Update stats
        app_state["query_count"] += 1
        app_state["total_time"] += elapsed
        app_state["history"].append({
            "query_id": query_id,
            "question": req.question,
            "time": round(elapsed, 2),
            "timestamp": datetime.utcnow().isoformat(),
        })

        return QueryResponse(
            answer=result.get("answer", "No answer"),
            sources=sources,
            language=result.get("language", "unknown"),
            processing_time=round(elapsed, 3),
            query_id=query_id,
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def stats():
    count = app_state["query_count"]
    avg = app_state["total_time"] / count if count else 0
    return {
        "total_queries": count,
        "avg_response_time": round(avg, 3),
        "recent_queries": app_state["history"][-10:],
    }


@app.get("/api/history")
async def history(limit: int = 50):
    return {
        "queries": app_state["history"][-limit:],
        "total": len(app_state["history"]),
    }


@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "timestamp": datetime.utcnow().isoformat()},
    )


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("CUSB AI ASSISTANT - PRODUCTION API SERVER")
    print("=" * 70)
    print("\nEndpoints:")
    print("  GET  /            - API info")
    print("  GET  /api/health  - Health check")
    print("  POST /api/query   - Ask questions")
    print("  GET  /api/stats   - Statistics")
    print("  GET  /api/history - Query history")
    print("  GET  /docs        - Swagger UI")
    print("\nStarting server on http://localhost:8080")
    print("=" * 70)

    uvicorn.run("api_server:app", host="127.0.0.1", port=8080, reload=False)
