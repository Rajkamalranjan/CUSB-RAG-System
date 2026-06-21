"""Run the 1000-question research chat benchmark with retrieval metrics.

Examples:
    python scripts/research_chat_eval.py --limit 20 --delay 1
    python scripts/research_chat_eval.py --delay 10
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_QUESTIONS = Path("evaluation/research_1000_questions.jsonl")
DEFAULT_REPORT_DIR = Path("reports/evaluation")

HINGLISH_MARKERS = (
    "hai", "hain", "kya", "ka", "ke", "ki", "mein", "batao",
    "kaise", "kitna", "kitni", "kaha", "kahan", "hota", "hoti",
    "chahiye", "kare", "karein", "nahi", "sakte", "sakta", "sakti",
    "kab", "hua", "tha", "aur", "se", "par",
)

NOT_FOUND_MARKERS = (
    "could not find",
    "i could not find",
    "available cusb data",
    "information nahi mili",
    "data me nahi mila",
    "could not verify this programme",
    "course verify nahi hua",
)

BAD_TEXT_MARKERS = ("Ã", "Â", "ï¿½", "\ufffd")


def read_questions(path: Path, limit: int | None, offset: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index < offset:
                continue
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


def post_chat_with_retry(api_url: str, query: str, timeout: int, retries: int, retry_delay: float) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return post_chat(api_url, query, timeout)
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                raise
            time.sleep(retry_delay * (attempt + 1))
    raise RuntimeError(str(last_error or "chat request failed"))


def normalize(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def looks_hinglish(text: str) -> bool:
    lowered = normalize(text)
    if re.search(r"[\u0900-\u097f]", text):
        return True
    return any(re.search(rf"\b{re.escape(marker)}\b", lowered) for marker in HINGLISH_MARKERS)


def is_not_found(answer: str) -> bool:
    lowered = normalize(answer)
    return any(marker in lowered for marker in NOT_FOUND_MARKERS)


def source_blob(source: dict[str, Any]) -> str:
    parts = [
        source.get("title"),
        source.get("url"),
        source.get("source"),
        source.get("source_file"),
        source.get("file"),
        source.get("department"),
        source.get("category"),
        source.get("text"),
        source.get("snippet"),
        source.get("content"),
    ]
    metadata = source.get("metadata")
    if isinstance(metadata, dict):
        parts.extend(str(value) for value in metadata.values())
    return normalize(" ".join(str(part or "") for part in parts))


def term_hits(text: str, terms: list[str]) -> int:
    lowered = normalize(text)
    compact = re.sub(r"[^a-z0-9]+", "", lowered)
    aliases = {
        "location": ("location", "located", "address"),
        "vc": ("vc", "vice-chancellor", "vice chancellor"),
        "mcom": ("mcom", "m.com", "m.com."),
        "wifi": ("wifi", "wi-fi"),
        "admission notice": ("admission notice", "admission/notice", "admission notification"),
        "fee payment": ("fee payment", "fee-payment"),
        "medical support": ("medical support", "health centre", "health center", "jeevak"),
        "career": ("career", "career counselling", "placement cell"),
    }
    hits = 0
    for term in terms:
        normalized_term = normalize(term)
        if not normalized_term:
            continue
        candidates = aliases.get(normalized_term, (normalized_term,))
        if any(
            normalize(candidate) in lowered
            or re.sub(r"[^a-z0-9]+", "", normalize(candidate)) in compact
            for candidate in candidates
        ):
            hits += 1
    return hits


def source_relevance(sources: list[dict[str, Any]], terms: list[str]) -> list[int]:
    if not terms:
        return [0 for _ in sources]
    return [1 if term_hits(source_blob(source), terms) else 0 for source in sources]


def retrieval_metrics(sources: list[dict[str, Any]], terms: list[str], k: int = 5) -> dict[str, Any]:
    rel = source_relevance(sources, terms)
    top_rel = rel[:k]
    recall_at_k = 1.0 if any(top_rel) else 0.0
    first_rank = next((idx + 1 for idx, value in enumerate(rel) if value), None)
    mrr = 1.0 / first_rank if first_rank else 0.0
    dcg = sum(value / math.log2(index + 2) for index, value in enumerate(top_rel))
    ideal_count = min(sum(rel), k)
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_count))
    ndcg = dcg / idcg if idcg else 0.0
    return {
        "recall_at_5": round(recall_at_k, 4),
        "mrr": round(mrr, 4),
        "ndcg_at_5": round(ndcg, 4),
        "relevant_source_count": sum(rel),
        "first_relevant_rank": first_rank,
    }


def classify_answer(row: dict[str, Any], answer: str, error: str | None) -> str:
    if error:
        return "error"
    if any(marker in answer for marker in BAD_TEXT_MARKERS):
        return "incomplete"

    answerable = bool(row.get("answerable", True))
    not_found = is_not_found(answer)
    if not answerable:
        if not_found or len(answer.strip()) < 80:
            return "correct"
        return "hallucinated"

    if not_found:
        return "incomplete"
    if len(answer.strip()) < 20:
        return "incomplete"

    terms = row.get("expected_answer_terms") or row.get("expected_source_terms") or []
    hits = term_hits(answer, list(terms))
    if not terms:
        return "correct"
    required_hits = max(1, math.ceil(len(terms) * 0.5))
    if hits >= required_hits:
        return "correct"
    if hits >= 1:
        return "partially_correct"
    return "unsupported"


def classify_citation(row: dict[str, Any], sources: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
    if not row.get("answerable", True):
        return "not_applicable"
    if not sources:
        return "no_sources"
    if not (row.get("expected_source_terms") or []):
        return "not_applicable"
    if metrics["recall_at_5"] > 0:
        return "grounded"
    return "wrong_source"


def classify_language(row: dict[str, Any], answer: str, error: str | None) -> str:
    if error:
        return "error"
    expected = row.get("language")
    query = str(row.get("query") or "")
    # Short or label-like inputs such as "fees" and "hostel" do not encode a language.
    if expected == "hinglish" and not looks_hinglish(query):
        return "not_checked"
    if expected == "hinglish":
        return "ok" if looks_hinglish(answer) or is_not_found(answer) else "wrong_language"
    if expected == "english":
        return "wrong_language" if looks_hinglish(answer) and not is_not_found(answer) else "ok"
    return "not_checked"


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "total": len(results),
        "by_answer_quality": {},
        "by_language_quality": {},
        "by_citation_quality": {},
        "by_category": {},
        "by_robustness": {},
        "averages": {},
    }
    for result in results:
        for key, bucket in (
            ("answer_quality", "by_answer_quality"),
            ("language_quality", "by_language_quality"),
            ("citation_quality", "by_citation_quality"),
            ("category", "by_category"),
            ("robustness", "by_robustness"),
        ):
            value = result.get(key)
            summary[bucket][value] = summary[bucket].get(value, 0) + 1

    metric_names = ("recall_at_5", "mrr", "ndcg_at_5", "relevant_source_count")
    for name in metric_names:
        values = [float(result.get(name) or 0) for result in results]
        summary["averages"][name] = round(sum(values) / len(values), 4) if values else 0.0
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--api", default="http://localhost:8080")
    parser.add_argument("--delay", type=float, default=10.0)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-delay", type=float, default=3.0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    questions = read_questions(args.questions, args.limit, args.offset)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"research_chat_eval_{timestamp}.json"
    csv_path = args.out_dir / f"research_chat_eval_{timestamp}.csv"

    results: list[dict[str, Any]] = []
    for index, row in enumerate(questions, 1):
        started = time.perf_counter()
        error = None
        data: dict[str, Any] = {}
        try:
            data = post_chat_with_retry(args.api, row["query"], args.timeout, args.retries, args.retry_delay)
        except urllib.error.HTTPError as exc:
            error = f"HTTP {exc.code}: {exc.reason}"
        except Exception as exc:
            error = str(exc)

        answer = str(data.get("answer") or "")
        sources = data.get("sources") or []
        if not isinstance(sources, list):
            sources = []
        metrics = retrieval_metrics(sources, list(row.get("expected_source_terms") or []))
        answer_quality = classify_answer(row, answer, error)
        language_quality = classify_language(row, answer, error)
        citation_quality = classify_citation(row, sources, metrics)
        status = "OK"
        if error:
            status = "Error"
        elif answer_quality in {"hallucinated", "unsupported"}:
            status = "Weak"
        elif answer_quality in {"partially_correct", "incomplete"}:
            status = "Partial"
        if language_quality == "wrong_language":
            status = "Wrong Language"
        if citation_quality == "wrong_source" and status == "OK" and answer_quality != "correct":
            status = "Citation Weak"

        result = {
            "id": row.get("id"),
            "category": row.get("category"),
            "query": row.get("query"),
            "expected_language": row.get("language"),
            "answerable": row.get("answerable", True),
            "robustness": row.get("robustness"),
            "status": status,
            "answer_quality": answer_quality,
            "language_quality": language_quality,
            "citation_quality": citation_quality,
            "source_count": len(sources),
            "confidence": data.get("confidence"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": error,
            "answer": answer,
            **metrics,
        }
        results.append(result)
        print(
            f"{index:04d}/{len(questions):04d} {status}: "
            f"{row.get('category')} | {row['query']}"
        )
        if index < len(questions):
            time.sleep(args.delay)

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api": args.api,
        "delay_seconds": args.delay,
        "question_count": len(results),
        "summary": summarize(results),
        "results": results,
    }
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = [
        "id", "category", "query", "expected_language", "answerable", "robustness",
        "status", "answer_quality", "language_quality", "citation_quality",
        "recall_at_5", "mrr", "ndcg_at_5", "relevant_source_count",
        "first_relevant_rank", "source_count", "confidence", "latency_ms",
        "error", "answer",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_ALL,
            escapechar="\\",
        )
        writer.writeheader()
        for result in results:
            writer.writerow({key: result.get(key) for key in fieldnames})

    summary = report["summary"]
    print("\nAnswer quality:", summary["by_answer_quality"])
    print("Language quality:", summary["by_language_quality"])
    print("Citation quality:", summary["by_citation_quality"])
    print("Averages:", summary["averages"])
    print("JSON:", json_path)
    print("CSV:", csv_path)

    bad_statuses = {"Error", "Wrong Language"}
    return 1 if any(result["status"] in bad_statuses for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
