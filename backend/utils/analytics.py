"""Append-only JSONL analytics for local no-Docker deployments."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_PATH = Path("reports/chat_logs.jsonl")


def log_chat_event(event: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def analytics_summary(limit: int = 200) -> dict[str, Any]:
    if not LOG_PATH.exists():
        return {"total_logged": 0, "recent": [], "most_asked": [], "failed_recent": [], "weak_feedback": []}
    rows = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    recent = rows[-limit:]
    failed = [row for row in rows if row.get("not_found")]
    query_rows = [row for row in rows if row.get("query")]
    most_asked = Counter(str(row["query"]).strip() for row in query_rows if str(row["query"]).strip())
    weak_feedback = [
        row for row in rows
        if row.get("feedback") and str(row.get("feedback", {}).get("rating", "")).lower() in {"weak", "bad", "down"}
    ]
    latencies = [float(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None]
    return {
        "total_logged": len(rows),
        "failed_queries": len(failed),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "most_asked": [{"query": query, "count": count} for query, count in most_asked.most_common(20)],
        "failed_recent": failed[-25:],
        "weak_feedback": weak_feedback[-25:],
        "recent": recent,
    }
