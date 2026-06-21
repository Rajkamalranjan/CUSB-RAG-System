"""Async ingestion and indexing tasks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.worker import celery_app


@celery_app.task(name="ingest_uploaded_pdf")
def ingest_uploaded_pdf(path: str) -> dict:
    pdf_path = Path(path)
    if not pdf_path.exists():
        return {"status": "failed", "error": f"file not found: {path}"}
    from ingestion.loaders.incremental_indexer import index_pdf_incremental

    return index_pdf_incremental(pdf_path)


@celery_app.task(name="reindex_all")
def reindex_all() -> dict:
    subprocess.run([sys.executable, "scripts/ingest_all.py"], check=True)
    return {"status": "ok"}


@celery_app.task(name="index_qdrant")
def index_qdrant() -> dict:
    subprocess.run([sys.executable, "scripts/index_qdrant.py"], check=True)
    return {"status": "ok"}
