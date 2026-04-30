"""
LLM-as-Judge Evaluation Framework

Evaluates RAG answers using an LLM to score:
- Faithfulness: Answer follows retrieved context
- Correctness: Answer is factually accurate
- Helpfulness: Answer addresses user query effectively
- Completeness: Answer covers all important aspects
- Language Quality: Grammar, clarity, and fluency
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.generativeai as genai
from tqdm import tqdm

from config import (
    ENABLE_LLM_JUDGE,
    EVAL_DIR,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_JUDGE_MODEL,
    LLM_PROVIDER,
    SIGNIFICANCE_THRESHOLD,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


JUDGE_PROMPT_TEMPLATE = """You are an expert evaluator of Question-Answering systems. 
Evaluate the following answer based on the provided context and reference answer.

CONTEXT:
{context}

QUESTION:
{question}

GENERATED ANSWER:
{answer}

REFERENCE ANSWER (if available):
{reference}

Please evaluate on the following criteria (1-5 scale):

1. **Faithfulness** (1-5): Does the answer stay faithful to the provided context? 
   - 5: Answer only uses information from context
   - 3: Mostly from context with minor inference
   - 1: Contains information not in context

2. **Correctness** (1-5): Is the answer factually accurate?
   - 5: Completely accurate
   - 3: Mostly accurate with minor errors
   - 1: Contains significant errors

3. **Helpfulness** (1-5): Does the answer effectively address the question?
   - 5: Fully addresses the question with relevant details
   - 3: Addresses question but lacks some details
   - 1: Doesn't address the question

4. **Completeness** (1-5): Does the answer cover important aspects?
   - 5: Comprehensive coverage of all important points
   - 3: Covers main points but misses some details
   - 1: Incomplete coverage

5. **Language Quality** (1-5): Grammar, clarity, and fluency?
   - 5: Excellent grammar and clarity
   - 3: Good grammar with minor issues
   - 1: Poor grammar and clarity

Respond in JSON format:
{{
    "faithfulness": <1-5>,
    "correctness": <1-5>,
    "helpfulness": <1-5>,
    "completeness": <1-5>,
    "language_quality": <1-5>,
    "overall_score": <average of above>,
    "strengths": "<brief description>",
    "weaknesses": "<brief description>",
    "explanation": "<brief explanation of scores>"
}}"""


class LLMJudge:
    """LLM-based judge for evaluating RAG outputs."""

    def __init__(self, model: str = LLM_JUDGE_MODEL):
        self.model = model
        self.provider = LLM_PROVIDER.lower()

        if self.provider == "groq" and GROQ_API_KEY:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY)
            self.groq_model = GROQ_MODEL
            self.model_obj = None
            print(f"⚖️  Judge using Groq ({self.groq_model})")
        elif GEMINI_API_KEY:
            self.model_obj = genai.GenerativeModel(model)
            self.groq_client = None
            print(f"⚖️  Judge using Gemini ({model})")
        else:
            self.model_obj = None
            self.groq_client = None
            print("⚠️  No API key available for judge")

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        context: str,
        reference: str = "",
    ) -> dict[str, Any]:
        """
        Evaluate a generated answer using LLM-as-judge.

        Args:
            question: User query
            answer: Generated answer
            context: Retrieved context
            reference: Reference/ground truth answer (optional)

        Returns:
            Dictionary with scores and explanation
        """
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            context=context[:2000],  # Limit context length
            question=question,
            answer=answer,
            reference=reference or "Not provided"
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use Groq or Gemini based on provider
                if self.groq_client:
                    response = self.groq_client.chat.completions.create(
                        model=self.groq_model,
                        messages=[
                            {"role": "system", "content": "You are an expert evaluator. Respond ONLY with valid JSON."},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=512,
                        temperature=0.1,
                    )
                    text = response.choices[0].message.content.strip()
                elif self.model_obj:
                    response = self.model_obj.generate_content(prompt)
                    text = response.text
                else:
                    return {"error": "No LLM available", "faithfulness": 0, "correctness": 0, "helpfulness": 0, "completeness": 0, "language_quality": 0, "overall_score": 0}

                # Extract JSON from response
                import re
                json_match = re.search(r"\{.*\}", text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    result["raw_response"] = text
                    return result

                return {
                    "error": "Could not parse response",
                    "raw_response": text,
                    "faithfulness": 0,
                    "correctness": 0,
                    "helpfulness": 0,
                    "completeness": 0,
                    "language_quality": 0,
                    "overall_score": 0,
                }

            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries - 1:
                    wait_time = 35 * (attempt + 1)
                    print(f"\n    ⏳ Rate limited, waiting {wait_time}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                return {
                    "error": error_str,
                    "faithfulness": 0,
                    "correctness": 0,
                    "helpfulness": 0,
                    "completeness": 0,
                    "language_quality": 0,
                    "overall_score": 0,
                }

    def batch_evaluate(
        self,
        results_path: Path,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """
        Batch evaluate results from benchmark/evaluation runs.

        Args:
            results_path: Path to JSONL file with benchmark results
            output_path: Output path for judged results

        Returns:
            Dictionary with aggregated statistics
        """
        if output_path is None:
            output_path = EVAL_DIR / f"llm_judge_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"

        results = []
        scores = {
            "faithfulness": [],
            "correctness": [],
            "helpfulness": [],
            "completeness": [],
            "language_quality": [],
            "overall_score": [],
        }

        # Read results
        with open(results_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Skip metadata line
        data_lines = [l for l in lines if not l.strip().startswith('{"type": "metadata"')]

        print(f"\n📊 Starting LLM-as-Judge evaluation on {len(data_lines)} results...")

        for line in tqdm(data_lines, desc="Evaluating"):
            try:
                item = json.loads(line)

                # Extract components
                question = item.get("query", "")
                answer = item.get("answer", "")
                sources = item.get("sources", [])

                # Use full context from result if available, else reconstruct from sources
                context = item.get("context", "")
                if not context:
                    context_parts = [
                        f"Source {i+1}: {s.get('heading', 'Unknown')}\n{s.get('text', '')[:500]}"
                        for i, s in enumerate(sources[:3])
                    ]
                    context = "\n\n".join(context_parts)

                # Get judge scores
                judge_scores = self.evaluate_answer(
                    question=question,
                    answer=answer,
                    context=context,
                    reference="",
                )

                # Append scores
                for key in scores:
                    if key in judge_scores:
                        scores[key].append(judge_scores[key])

                # Delay between evaluations to avoid rate limit
                time.sleep(3)

                # Save result
                item["judge_scores"] = judge_scores
                results.append(item)

            except Exception as e:
                print(f"⚠️  Error evaluating: {e}")
                continue

        # Write results
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        # Calculate statistics
        stats = {
            "total_evaluated": len(results),
            "output_file": str(output_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for metric, values in scores.items():
            if values:
                stats[metric] = {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "std": (sum((x - sum(values)/len(values))**2 for x in values) / len(values)) ** 0.5,
                }

        return stats


def main():
    """Run LLM-as-Judge evaluation on latest benchmark results."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=None,
        help="Path to benchmark results JSONL file"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for judged results"
    )
    args = parser.parse_args()

    if not ENABLE_LLM_JUDGE:
        print("❌ LLM-as-Judge is disabled. Set ENABLE_LLM_JUDGE=true in .env")
        return

    # Find latest benchmark if not specified
    input_path = args.input
    if not input_path:
        reports_dir = Path("reports")
        benchmark_files = sorted(reports_dir.glob("rag_benchmark_*.jsonl"))
        if not benchmark_files:
            print("❌ No benchmark files found in reports/")
            return
        input_path = benchmark_files[-1]

    input_path = Path(input_path)
    print(f"\n📁 Input: {input_path}")

    judge = LLMJudge()
    stats = judge.batch_evaluate(input_path, Path(args.output) if args.output else None)

    print("\n" + "=" * 80)
    print("LLM-AS-JUDGE EVALUATION RESULTS")
    print("=" * 80)

    print(f"\n✅ Evaluated {stats['total_evaluated']} results")
    print(f"📊 Output: {stats['output_file']}")

    print("\n📈 AGGREGATE SCORES:")
    for metric, values in stats.items():
        if isinstance(values, dict):
            print(f"  {metric.upper()}:")
            print(f"    Mean: {values['mean']:.2f}")
            print(f"    Min:  {values['min']:.2f}")
            print(f"    Max:  {values['max']:.2f}")
            print(f"    Std:  {values['std']:.2f}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
