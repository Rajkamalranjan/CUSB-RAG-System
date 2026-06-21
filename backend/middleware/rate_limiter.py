"""In-memory rate limiting for local deployments."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request


_hits: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(max_requests: int, window_seconds: int) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        forwarded = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded.split(",")[0].strip() if forwarded else None
        if not client_ip and request.client:
            client_ip = request.client.host
        key = f"{client_ip or 'unknown'}:{request.url.path}"
        now = time.monotonic()
        bucket = _hits[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        bucket.append(now)

    return dependency
