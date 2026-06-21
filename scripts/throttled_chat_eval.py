"""Run throttled chat regression tests and write JSON/CSV reports.

Example:
    python scripts/throttled_chat_eval.py --delay 6 --limit 100
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_QUESTIONS = Path("evaluation/general_student_questions.jsonl")
DEFAULT_REPORT_DIR = Path("reports/evaluation")


HINGLISH_MARKERS = (
    " hai", " hain", " kya", " ka ", " ke ", " ki ", " me ", " mein ", " batao",
    " kaise", " kitna", " kitni", " kaha", " kahan", " hota", " hoti", " chahiye",
    " karein", " check karein", " haan", " nahi", " ke liye", " ke hisaab",
)

ENGLISH_MARKERS = (
    " the ", " is ", " are ", " should ", " students ", " please ", " verify ",
    " available ", " published ", " admission ", " current ", " latest ",
)


def read_questions(path: Path, limit: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


def post_chat(api_url: str, query: str, timeout: int) -> dict[str, Any]:
    payload = json.dumps({"query": query, "filters": {}}).encode("utf-8")
    request = urllib.request.Request(
        api_url.rstrip("/") + "/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def looks_hinglish(text: str) -> bool:
    lowered = f" {text.lower()} "
    return bool(re.search(r"[\u0900-\u097f]", text)) or any(marker in lowered for marker in HINGLISH_MARKERS)


def looks_english(text: str) -> bool:
    lowered = f" {text.lower()} "
    return any(marker in lowered for marker in ENGLISH_MARKERS)


def classify(row: dict[str, Any], answer: str, error: str | None) -> str:
    if error:
        return "Error"
    lowered = answer.lower()
    if "i could not find this" in lowered or "information nahi mili" in lowered or "could not find" in lowered:
        return "Not Found"
    if any(bad in answer for bad in ("â", "ð", "�")):
        return "Weak"
    expected = row.get("language")
    if expected == "hinglish" and not looks_hinglish(answer):
        return "Wrong Language"
    if expected == "english" and looks_hinglish(answer) and not looks_english(answer):
        return "Wrong Language"
    if len(answer.strip()) < 20:
        return "Weak"
    return "OK"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--api", default="http://localhost:8080")
    parser.add_argument("--delay", type=float, default=6.0)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    questions = read_questions(args.questions, args.limit)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"chat_eval_{timestamp}.json"
    csv_path = args.out_dir / f"chat_eval_{timestamp}.csv"

    results: list[dict[str, Any]] = []
    for index, row in enumerate(questions, 1):
        started = time.perf_counter()
        error = None
        data: dict[str, Any] = {}
        try:
            data = post_chat(args.api, row["query"], args.timeout)
        except urllib.error.HTTPError as exc:
            error = f"HTTP {exc.code}: {exc.reason}"
        except Exception as exc:  # pragma: no cover - command-line resilience
            error = str(exc)

        answer = str(data.get("answer") or "")
        status = classify(row, answer, error)
        result = {
            "id": row.get("id"),
            "query": row["query"],
            "expected_language": row.get("language"),
            "tags": row.get("tags", []),
            "status": status,
            "answer": answer,
            "source_count": len(data.get("sources") or []),
            "confidence": data.get("confidence"),
            "error": error,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        results.append(result)
        print(f"{index:03d}/{len(questions):03d} {status}: {row['query']}")
        if index < len(questions):
            time.sleep(args.delay)

    summary: dict[str, int] = {}
    for result in results:
        summary[result["status"]] = summary.get(result["status"], 0) + 1

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api": args.api,
        "delay_seconds": args.delay,
        "question_count": len(results),
        "summary": summary,
        "results": results,
    }
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id", "query", "expected_language", "status", "source_count",
                "confidence", "latency_ms", "error", "answer",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow({key: result.get(key) for key in writer.fieldnames})

    print("\nSummary:", summary)
    print("JSON:", json_path)
    print("CSV:", csv_path)
    return 0 if not any(r["status"] in {"Error", "Wrong Language"} for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
