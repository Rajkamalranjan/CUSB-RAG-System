"""Prometheus metrics used by FastAPI routes."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, generate_latest


CHAT_REQUESTS = Counter("cusb_chat_requests_total", "Total chat requests", ["status"])
CHAT_LATENCY = Histogram("cusb_chat_latency_seconds", "Chat endpoint latency")
UPLOAD_REQUESTS = Counter("cusb_upload_requests_total", "Total upload requests", ["status"])


def metrics_text() -> bytes:
    return generate_latest()
