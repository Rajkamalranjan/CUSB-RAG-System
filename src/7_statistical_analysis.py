"""
Statistical Analysis and Hypothesis Testing Module

Provides statistical analysis tools for RAG evaluation:
- Descriptive statistics
- Significance testing (t-tests, Mann-Whitney U)
- Effect size calculation (Cohen's d)
- Confidence intervals
- Statistical summaries for research papers
"""

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

from config import EVAL_DIR, SIGNIFICANCE_THRESHOLD

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class StatisticalAnalyzer:
    """Statistical analysis for RAG evaluation results."""

    def __init__(self, significance_level: float = SIGNIFICANCE_THRESHOLD):
        self.significance_level = significance_level

    @staticmethod
    def describe(values: list[float]) -> dict[str, float]:
        """
        Calculate descriptive statistics.

        Args:
            values: List of numeric values

        Returns:
            Dictionary with statistics
        """
        if not values:
            return {}

        arr = np.array(values)
        return {
            "count": len(values),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)),
            "variance": float(np.var(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "q1": float(np.percentile(arr, 25)),
            "q3": float(np.percentile(arr, 75)),
            "iqr": float(np.percentile(arr, 75) - np.percentile(arr, 25)),
        }

    @staticmethod
    def confidence_interval(
        values: list[float],
        confidence: float = 0.95
    ) -> tuple[float, float]:
        """
        Calculate confidence interval for mean.

        Args:
            values: List of numeric values
            confidence: Confidence level (default 0.95)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        arr = np.array(values)
        mean = np.mean(arr)
        sem = stats.sem(arr)
        ci = sem * stats.t.ppf((1 + confidence) / 2, len(arr) - 1)
        return (float(mean - ci), float(mean + ci))

    @staticmethod
    def cohens_d(group1: list[float], group2: list[float]) -> float:
        """
        Calculate Cohen's d effect size.

        Args:
            group1: First group of values
            group2: Second group of values

        Returns:
            Cohen's d value
        """
        arr1 = np.array(group1)
        arr2 = np.array(group2)

        n1, n2 = len(arr1), len(arr2)
        var1, var2 = np.var(arr1, ddof=1), np.var(arr2, ddof=1)
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

        if pooled_std == 0:
            return 0.0

        return float((np.mean(arr1) - np.mean(arr2)) / pooled_std)

    def ttest_independent(
        self,
        group1: list[float],
        group2: list[float],
        equal_var: bool = True
    ) -> dict[str, Any]:
        """
        Independent samples t-test.

        Args:
            group1: First group of values
            group2: Second group of values
            equal_var: Assume equal variances

        Returns:
            Dictionary with test results
        """
        t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=equal_var)

        return {
            "test": "Independent t-test",
            "t_statistic": float(t_stat),
            "p_value": float(p_value),
            "significant": p_value < self.significance_level,
            "cohens_d": self.cohens_d(group1, group2),
            "group1_mean": float(np.mean(group1)),
            "group2_mean": float(np.mean(group2)),
            "difference": float(np.mean(group1) - np.mean(group2)),
        }

    def mannwhitneyu_test(
        self,
        group1: list[float],
        group2: list[float]
    ) -> dict[str, Any]:
        """
        Mann-Whitney U test (non-parametric).

        Args:
            group1: First group of values
            group2: Second group of values

        Returns:
            Dictionary with test results
        """
        u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative="two-sided")

        return {
            "test": "Mann-Whitney U",
            "u_statistic": float(u_stat),
            "p_value": float(p_value),
            "significant": p_value < self.significance_level,
            "rank_biserial": float(1 - 2 * u_stat / (len(group1) * len(group2))),
        }

    def anova_test(self, *groups: list[float]) -> dict[str, Any]:
        """
        One-way ANOVA test.

        Args:
            *groups: Variable number of groups

        Returns:
            Dictionary with test results
        """
        f_stat, p_value = stats.f_oneway(*groups)

        return {
            "test": "One-way ANOVA",
            "f_statistic": float(f_stat),
            "p_value": float(p_value),
            "significant": p_value < self.significance_level,
            "num_groups": len(groups),
            "group_means": [float(np.mean(g)) for g in groups],
        }

    def correlation_pearson(
        self,
        x: list[float],
        y: list[float]
    ) -> dict[str, Any]:
        """
        Pearson correlation test.

        Args:
            x: First variable
            y: Second variable

        Returns:
            Dictionary with correlation results
        """
        r, p_value = stats.pearsonr(x, y)

        return {
            "test": "Pearson Correlation",
            "correlation": float(r),
            "p_value": float(p_value),
            "significant": p_value < self.significance_level,
            "r_squared": float(r ** 2),
        }

    def correlation_spearman(
        self,
        x: list[float],
        y: list[float]
    ) -> dict[str, Any]:
        """
        Spearman correlation test (non-parametric).

        Args:
            x: First variable
            y: Second variable

        Returns:
            Dictionary with correlation results
        """
        rho, p_value = stats.spearmanr(x, y)

        return {
            "test": "Spearman Correlation",
            "correlation": float(rho),
            "p_value": float(p_value),
            "significant": p_value < self.significance_level,
        }


class ResultsAnalyzer:
    """Analyze benchmark and evaluation results."""

    def __init__(self):
        self.analyzer = StatisticalAnalyzer()

    def load_results(self, path: Path) -> list[dict]:
        """Load results from JSONL file."""
        results = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
        return results

    def extract_metrics(self, results: list[dict]) -> dict[str, list[float]]:
        """Extract metrics from results."""
        metrics = {
            "latency_ms": [],
            "overall_score": [],
            "faithfulness": [],
            "correctness": [],
            "helpfulness": [],
        }

        # Handle baseline_comparison format (single JSON with nested baselines)
        if len(results) == 1 and "baselines" in results[0]:
            baselines = results[0]["baselines"]
            for baseline_name, baseline_data in baselines.items():
                if "results" in baseline_data:
                    for result in baseline_data["results"]:
                        if "latency_ms" in result:
                            metrics["latency_ms"].append(result["latency_ms"])
                if "avg_latency_ms" in baseline_data:
                    metrics["latency_ms"].append(baseline_data["avg_latency_ms"])
            return {k: v for k, v in metrics.items() if v}

        # Handle ablation study format (single JSON with nested models)
        if len(results) == 1 and "models" in results[0]:
            for model_data in results[0]["models"]:
                if "queries" in model_data:
                    for query in model_data["queries"]:
                        if "latency_ms" in query:
                            metrics["latency_ms"].append(query["latency_ms"])
                if "total_latency_ms" in model_data:
                    metrics["latency_ms"].append(model_data["total_latency_ms"])
            return {k: v for k, v in metrics.items() if v}

        # Handle context window ablation format
        if len(results) == 1 and "context_windows" in results[0]:
            for window_data in results[0]["context_windows"]:
                if "queries" in window_data:
                    for query in window_data["queries"]:
                        if "latency_ms" in query:
                            metrics["latency_ms"].append(query["latency_ms"])
                if "avg_latency_ms" in window_data:
                    metrics["latency_ms"].append(window_data["avg_latency_ms"])
            return {k: v for k, v in metrics.items() if v}

        # Handle top-k ablation format
        if len(results) == 1 and "top_k_values" in results[0]:
            for topk_data in results[0]["top_k_values"]:
                if "queries" in topk_data:
                    for query in topk_data["queries"]:
                        if "latency_ms" in query:
                            metrics["latency_ms"].append(query["latency_ms"])
                if "avg_latency_ms" in topk_data:
                    metrics["latency_ms"].append(topk_data["avg_latency_ms"])
            return {k: v for k, v in metrics.items() if v}

        # Handle standard format
        for result in results:
            if "latency_ms" in result:
                metrics["latency_ms"].append(result["latency_ms"])

            if "judge_scores" in result:
                scores = result["judge_scores"]
                if "overall_score" in scores:
                    metrics["overall_score"].append(scores["overall_score"])
                if "faithfulness" in scores:
                    metrics["faithfulness"].append(scores["faithfulness"])
                if "correctness" in scores:
                    metrics["correctness"].append(scores["correctness"])
                if "helpfulness" in scores:
                    metrics["helpfulness"].append(scores["helpfulness"])

        return {k: v for k, v in metrics.items() if v}

    def analyze_results(self, path: Path) -> dict[str, Any]:
        """Comprehensive analysis of results."""
        results = self.load_results(path)
        metrics = self.extract_metrics(results)

        analysis = {
            "file": str(path),
            "num_results": len(results),
            "metrics": {},
        }

        for metric_name, values in metrics.items():
            if values:
                analysis["metrics"][metric_name] = self.analyzer.describe(values)
                analysis["metrics"][metric_name]["confidence_interval"] = (
                    self.analyzer.confidence_interval(values)
                )

        return analysis

    def compare_results(
        self,
        path1: Path,
        path2: Path,
        metric: str = "overall_score"
    ) -> dict[str, Any]:
        """Compare two result files."""
        results1 = self.load_results(path1)
        results2 = self.load_results(path2)

        metrics1 = self.extract_metrics(results1)
        metrics2 = self.extract_metrics(results2)

        if metric not in metrics1 or metric not in metrics2:
            error_msg = f"Metric '{metric}' not found in results. Available in file1: {list(metrics1.keys())}, file2: {list(metrics2.keys())}"
            return {"error": error_msg}

        values1 = metrics1[metric]
        values2 = metrics2[metric]

        comparison = {
            "metric": metric,
            "file1": str(path1),
            "file2": str(path2),
            "file1_stats": self.analyzer.describe(values1),
            "file2_stats": self.analyzer.describe(values2),
            "ttest": self.analyzer.ttest_independent(values1, values2),
            "mannwhitney": self.analyzer.mannwhitneyu_test(values1, values2),
        }

        return comparison


def main():
    """Main analysis script."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", help="Analyze single results file")
    parser.add_argument("--compare", nargs=2, help="Compare two results files")
    parser.add_argument("--metric", default="overall_score", help="Metric to compare")
    args = parser.parse_args()

    analyzer = ResultsAnalyzer()

    if args.analyze:
        path = Path(args.analyze)
        print(f"\n📊 Analyzing: {path}")
        analysis = analyzer.analyze_results(path)

        print("\n" + "=" * 80)
        print("STATISTICAL ANALYSIS RESULTS")
        print("=" * 80)

        for metric, stats in analysis["metrics"].items():
            print(f"\n📈 {metric.upper()}:")
            print(f"  Count:    {stats['count']}")
            print(f"  Mean:     {stats['mean']:.4f}")
            print(f"  Median:   {stats['median']:.4f}")
            print(f"  Std Dev:  {stats['std']:.4f}")
            print(f"  Min:      {stats['min']:.4f}")
            print(f"  Max:      {stats['max']:.4f}")
            ci_low, ci_high = stats["confidence_interval"]
            print(f"  95% CI:   [{ci_low:.4f}, {ci_high:.4f}]")

    elif args.compare:
        path1, path2 = Path(args.compare[0]), Path(args.compare[1])
        print(f"\n📊 Comparing:")
        print(f"  File 1: {path1}")
        print(f"  File 2: {path2}")
        print(f"  Metric: {args.metric}")

        comparison = analyzer.compare_results(path1, path2, args.metric)

        print("\n" + "=" * 80)
        print("COMPARISON RESULTS")
        print("=" * 80)

        if "error" in comparison:
            print(f"\n❌ {comparison['error']}")
            print("\n💡 Try comparing with 'latency_ms' instead:")
            print(f"   python src/7_statistical_analysis.py --compare {args.compare[0]} {args.compare[1]} --metric latency_ms")
        else:
            print(f"\n📊 {args.metric.upper()}:")
            print(f"  File 1 Mean: {comparison['file1_stats']['mean']:.4f}")
            print(f"  File 2 Mean: {comparison['file2_stats']['mean']:.4f}")
            print(f"  Difference: {comparison['file1_stats']['mean'] - comparison['file2_stats']['mean']:.4f}")

            print(f"\n🔬 Independent t-test:")
            ttest = comparison["ttest"]
            print(f"  t-statistic: {ttest['t_statistic']:.4f}")
            print(f"  p-value:     {ttest['p_value']:.4f}")
            print(f"  Significant: {'Yes' if ttest['significant'] else 'No'}")
            print(f"  Cohen's d:   {ttest['cohens_d']:.4f}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
