"""
Automated Baseline Evaluation - CUSB RAG System
Handles Windows Unicode issues properly
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix Windows Unicode
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

TEST_QUERIES = [
    {
        "id": 1,
        "query": "CUSB kya hai?",
        "category": "general",
        "expected_keywords": ["central university", "gaya", "bihar", "2009"],
    },
    {
        "id": 2,
        "query": "M.Sc Statistics ki fees kitni hai?",
        "category": "fees",
        "expected_keywords": ["26,072", "26072", "statistics", "fee"],
    },
    {
        "id": 3,
        "query": "Hostel fee kitni hai?",
        "category": "fees",
        "expected_keywords": ["9,000", "9000", "hostel", "mess"],
    },
    {
        "id": 4,
        "query": "Statistics department ke faculty kaun hain?",
        "category": "faculty",
        "expected_keywords": ["professor", "faculty", "sunit", "statistics"],
    },
    {
        "id": 5,
        "query": "Admission process kya hai?",
        "category": "admission",
        "expected_keywords": ["cuet", "entrance", "exam", "online"],
    },
    {
        "id": 6,
        "query": "CUSB ka NAAC grade kya hai?",
        "category": "general",
        "expected_keywords": ["naac", "a++", "grade"],
    },
    {
        "id": 7,
        "query": "M.Sc kitne courses hain CUSB mein?",
        "category": "courses",
        "expected_keywords": ["25", "mathematics", "statistics", "computer", "biotechnology"],
    },
    {
        "id": 8,
        "query": "Environmental Sciences ke HOD kaun hai?",
        "category": "faculty",
        "expected_keywords": ["hod", "head", "environmental", "dr"],
    },
    {
        "id": 9,
        "query": "CUET kya hai?",
        "category": "admission",
        "expected_keywords": ["cuet", "entrance", "exam", "common", "university"],
    },
    {
        "id": 10,
        "query": "PhD ki fees kitni hai?",
        "category": "fees",
        "expected_keywords": ["phd", "7,600", "7600", "5,000", "semester"],
    },
]


def check_keywords(answer, keywords):
    answer_lower = answer.lower()
    matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return matches / len(keywords) if keywords else 0


def main():
    print("=" * 70)
    print("BASELINE EVALUATION - CUSB RAG SYSTEM")
    print("=" * 70)

    # Load RAG pipeline
    print("\nLoading RAG pipeline...")
    try:
        from rag_engine import RAGPipeline
        rag = RAGPipeline()
        print("RAG pipeline loaded!\n")
    except Exception as e:
        print(f"Failed to load RAG: {e}")
        return

    results = []

    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"[{i}/10] {test['query']}", end=" ... ")

        start = time.time()
        try:
            response = rag.answer(test["query"])
            answer = response.get("answer", "")
            elapsed = time.time() - start

            score = check_keywords(answer, test["expected_keywords"])
            success = score >= 0.5 and len(answer) > 50

            result = {
                "id": test["id"],
                "query": test["query"],
                "category": test["category"],
                "answer": answer[:500],
                "keyword_score": round(score, 2),
                "response_time": round(elapsed, 2),
                "success": success,
                "expected_keywords": test["expected_keywords"],
                "keywords_matched": [kw for kw in test["expected_keywords"] if kw.lower() in answer.lower()],
            }
            results.append(result)

            status = "PASS" if success else "FAIL"
            print(f"{status} (score={score:.2f}, time={elapsed:.1f}s)")

        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "id": test["id"],
                "query": test["query"],
                "category": test["category"],
                "answer": f"ERROR: {e}",
                "keyword_score": 0,
                "response_time": 0,
                "success": False,
                "expected_keywords": test["expected_keywords"],
                "keywords_matched": [],
            })

    # Calculate summary
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    avg_time = sum(r["response_time"] for r in results) / total if total else 0
    avg_score = sum(r["keyword_score"] for r in results) / total if total else 0

    # Category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "scores": []}
        categories[cat]["total"] += 1
        if r["success"]:
            categories[cat]["passed"] += 1
        categories[cat]["scores"].append(r["keyword_score"])

    # Print report
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)

    print(f"\nOverall:")
    print(f"  Passed: {passed}/{total} ({passed/total*100:.0f}%)")
    print(f"  Avg Keyword Score: {avg_score:.2f}")
    print(f"  Avg Response Time: {avg_time:.2f}s")

    print(f"\nCategory Breakdown:")
    for cat, data in categories.items():
        cat_avg = sum(data["scores"]) / len(data["scores"])
        print(f"  {cat}: {data['passed']}/{data['total']} passed (avg score: {cat_avg:.2f})")

    print(f"\nDetailed Results:")
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        matched = r.get("keywords_matched", [])
        print(f"  [{status}] {r['query']}")
        print(f"    Score: {r['keyword_score']:.2f} | Time: {r['response_time']:.1f}s")
        print(f"    Keywords matched: {matched}")

    # Save report
    report_dir = Path(__file__).parent.parent / "reports"
    report_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"baseline_eval_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": round(passed / total, 2) if total else 0,
            "avg_keyword_score": round(avg_score, 2),
            "avg_response_time": round(avg_time, 2),
        },
        "categories": {cat: {
            "total": d["total"],
            "passed": d["passed"],
            "avg_score": round(sum(d["scores"]) / len(d["scores"]), 2)
        } for cat, d in categories.items()},
        "results": results,
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved: {report_file}")

    # Save markdown report
    md_file = report_dir / f"baseline_eval_{timestamp}.md"
    md_lines = [
        "# CUSB RAG Baseline Evaluation Report\n\n",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        f"**Overall Status:** {'PASS' if passed/total >= 0.7 else 'NEEDS IMPROVEMENT'}\n\n",
        "## Summary\n\n",
        f"| Metric | Value |\n|--------|-------|\n",
        f"| Total Queries | {total} |\n",
        f"| Passed | {passed} |\n",
        f"| Failed | {total - passed} |\n",
        f"| Success Rate | {passed/total*100:.0f}% |\n",
        f"| Avg Keyword Score | {avg_score:.2f} |\n",
        f"| Avg Response Time | {avg_time:.2f}s |\n\n",
        "## Category Breakdown\n\n",
        "| Category | Total | Passed | Avg Score |\n|----------|-------|--------|----------|\n",
    ]
    for cat, d in categories.items():
        cat_avg = sum(d["scores"]) / len(d["scores"])
        md_lines.append(f"| {cat} | {d['total']} | {d['passed']} | {cat_avg:.2f} |\n")

    md_lines.append("\n## Detailed Results\n\n")
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        md_lines.append(f"### {r['id']}. {r['query']} [{status}]\n\n")
        md_lines.append(f"- **Score:** {r['keyword_score']:.2f}\n")
        md_lines.append(f"- **Time:** {r['response_time']:.1f}s\n")
        md_lines.append(f"- **Keywords Matched:** {r.get('keywords_matched', [])}\n")
        md_lines.append(f"- **Answer:** {r['answer'][:200]}...\n\n")

    with open(md_file, "w", encoding="utf-8") as f:
        f.writelines(md_lines)

    print(f"Markdown report saved: {md_file}")
    print("\n" + "=" * 70)
    print("BASELINE EVALUATION COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
