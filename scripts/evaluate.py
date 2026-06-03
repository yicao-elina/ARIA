#!/usr/bin/env python3
"""ARIA Evaluation CLI.

Evaluate benchmark results using ARIA's metrics and optional LLM-as-Judge.

Usage:
    python scripts/evaluate.py --results benchmark_results/forward_prediction_results.json
    python scripts/evaluate.py --results benchmark_results/all_benchmark_results.json --judge
    python scripts/evaluate.py --task forward_prediction --output-dir eval_results
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure the aria package is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from aria.evaluation.metrics import MetricsComputer
from aria.evaluation.judge import LLMJudge

logger = logging.getLogger(__name__)

BENCHMARK_DIR = PROJECT_ROOT / "data" / "benchmarks"


def load_results(path: Path) -> List[Dict[str, Any]]:
    """Load benchmark results from a JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "results" in data:
        return data["results"]
    return [data]


def load_ground_truth(task_name: str) -> Dict[str, Dict[str, Any]]:
    """Load ground truth from benchmark JSONL files."""
    task_path = BENCHMARK_DIR / f"{task_name}.jsonl"
    if not task_path.exists():
        logger.warning("Ground truth file not found: %s", task_path)
        return {}

    ground_truth = {}
    with open(task_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            task = json.loads(line)
            task_id = task.get("id", "")
            ground_truth[task_id] = task
    return ground_truth


def compute_metrics(
    results: List[Dict[str, Any]],
    ground_truth: Dict[str, Dict[str, Any]],
    kg=None,
) -> List[Dict[str, Any]]:
    """Compute evaluation metrics for each result."""
    metrics_computer = MetricsComputer(kg=kg)
    evaluated = []

    for result in results:
        task_id = result.get("task_id", "")
        prediction = result.get("prediction", {})
        gt = ground_truth.get(task_id, {})
        ground_truth_answer = gt.get("expected_outcome", gt.get("expected_synthesis", ""))

        if not ground_truth_answer:
            logger.warning("No ground truth for task %s", task_id)
            evaluated.append({**result, "metrics": {}})
            continue

        try:
            metric_scores = metrics_computer.compute_all(
                prediction,
                {"answer": ground_truth_answer},
            )
            evaluated.append({**result, "metrics": metric_scores})
        except Exception as exc:
            logger.warning("Metrics computation failed for task %s: %s", task_id, exc)
            evaluated.append({**result, "metrics": {}, "metric_error": str(exc)})

    return evaluated


def run_judge(
    results: List[Dict[str, Any]],
    ground_truth: Dict[str, Dict[str, Any]],
    model: str = "qwen2:7b",
    backend: str = "ollama",
) -> List[Dict[str, Any]]:
    """Run LLM-as-Judge evaluation on results."""
    judge = LLMJudge(backend=backend, model=model)
    judged = []

    for result in results:
        task_id = result.get("task_id", "")
        gt = ground_truth.get(task_id, {})
        prediction = result.get("prediction", {})

        query = {
            "material": gt.get("input", {}).get("material", gt.get("target_material", "")),
            "target_property": gt.get("target_property", ""),
            "task_type": gt.get("task", "forward_prediction"),
        }
        ground_truth_dict = {
            "expected_outcome": gt.get("expected_outcome", gt.get("expected_synthesis", "")),
            "accepted_ranges": gt.get("accepted_ranges", {}),
            "expert_explanation": gt.get("expert_explanation", ""),
        }

        try:
            judge_result = judge.evaluate_all_metrics(query, prediction, ground_truth_dict)
            judged.append({**result, "judge_scores": judge_result})
        except Exception as exc:
            logger.warning("Judge evaluation failed for task %s: %s", task_id, exc)
            judged.append({**result, "judge_scores": {}, "judge_error": str(exc)})

    return judged


def main():
    parser = argparse.ArgumentParser(
        description="ARIA Evaluation CLI",
        prog="aria-evaluate",
    )
    parser.add_argument(
        "--results",
        type=str,
        help="Path to benchmark results JSON file",
    )
    parser.add_argument(
        "--task",
        choices=["forward_prediction", "inverse_design", "ood_generalization"],
        help="Which benchmark task to evaluate (loads ground truth)",
    )
    parser.add_argument(
        "--kg-file",
        type=str,
        help="Path to KG JSON file (for causal coherence metrics)",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Also run LLM-as-Judge evaluation",
    )
    parser.add_argument(
        "--judge-backend",
        default="ollama",
        choices=["ollama", "openai"],
        help="LLM backend for the judge",
    )
    parser.add_argument(
        "--judge-model",
        default="qwen2:7b",
        help="Model for the judge",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="eval_results",
        help="Directory to write evaluation results",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load results
    if args.results:
        results_path = Path(args.results)
        if not results_path.exists():
            logger.error("Results file not found: %s", results_path)
            sys.exit(1)
        results = load_results(results_path)
    elif args.task:
        # Auto-discover results file
        results_path = Path("benchmark_results") / f"{args.task}_results.json"
        if not results_path.exists():
            logger.error("No results file found at %s", results_path)
            sys.exit(1)
        results = load_results(results_path)
    else:
        logger.error("Specify --results or --task")
        sys.exit(1)

    logger.info("Loaded %d results", len(results))

    # Load ground truth
    task_name = args.task or "forward_prediction"
    ground_truth = load_ground_truth(task_name)
    logger.info("Loaded ground truth for %d tasks", len(ground_truth))

    # Load KG if provided
    kg = None
    if args.kg_file:
        from aria import load_kg
        kg = load_kg(args.kg_file)
        logger.info("Loaded KG from %s", args.kg_file)

    # Compute metrics
    logger.info("Computing evaluation metrics...")
    evaluated = compute_metrics(results, ground_truth, kg=kg)

    # Save evaluated results
    eval_path = output_dir / f"{task_name}_evaluated.json"
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(evaluated, f, indent=2, ensure_ascii=False)
    logger.info("Saved evaluated results to %s", eval_path)

    # Optional: LLM-as-Judge
    if args.judge:
        logger.info("Running LLM-as-Judge evaluation...")
        judged = run_judge(
            evaluated,
            ground_truth,
            model=args.judge_model,
            backend=args.judge_backend,
        )

        judge_path = output_dir / f"{task_name}_judge.json"
        with open(judge_path, "w", encoding="utf-8") as f:
            json.dump(judged, f, indent=2, ensure_ascii=False)
        logger.info("Saved judge results to %s", judge_path)

    # Print summary
    print("\n=== Evaluation Summary ===")
    print(f"Tasks evaluated: {len(evaluated)}")

    # Aggregate metrics
    metric_keys = set()
    for result in evaluated:
        metric_keys.update(result.get("metrics", {}).keys())

    for metric_name in sorted(metric_keys):
        values = [
            r.get("metrics", {}).get(metric_name, 0)
            for r in evaluated
            if isinstance(r.get("metrics", {}).get(metric_name), (int, float))
        ]
        if values:
            avg = sum(values) / len(values)
            print(f"  {metric_name}: mean={avg:.4f} (n={len(values)})")

    print(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()