"""
ARIA Benchmark Runner.

Loads JSONL benchmark files, runs all engine modes on tasks, computes
metrics, and produces comparison tables.  Provides a CLI entry point
via ``aria-benchmark``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from aria.evaluation.metrics import MetricsComputer
from aria.evaluation.judge import LLMJudge
from aria.types import ARIAResult, EngineMode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BenchmarkRunner
# ---------------------------------------------------------------------------

class BenchmarkRunner:
    """Orchestrate benchmark runs across ARIA engine modes.

    Parameters
    ----------
    kg :
        A NetworkX DiGraph representing the PSP knowledge graph.
    models :
        List of model identifiers to test (e.g. ``["qwen2:7b"]``).
    modes :
        List of :class:`EngineMode` values to evaluate.
        Defaults to all five modes.
    """

    def __init__(
        self,
        kg=None,
        models: Optional[Sequence[str]] = None,
        modes: Optional[Sequence[EngineMode]] = None,
    ):
        self.kg = kg
        self.models = list(models) if models else ["qwen2:7b"]
        self.modes = list(modes) if modes else list(EngineMode)

    # -- task loading -------------------------------------------------------

    @staticmethod
    def load_tasks(task_file: str) -> List[Dict[str, Any]]:
        """Load benchmark tasks from a JSONL file.

        Each line must be a JSON object with at least ``query`` and
        ``ground_truth`` keys.
        """
        tasks: List[Dict[str, Any]] = []
        with open(task_file, "r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    task = json.loads(line)
                    task.setdefault("id", f"task_{line_num}")
                    tasks.append(task)
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed line %d in %s", line_num, task_file)
        logger.info("Loaded %d tasks from %s", len(tasks), task_file)
        return tasks

    # -- single-run helper --------------------------------------------------

    def _run_single(
        self,
        task: Dict[str, Any],
        model: str,
        mode: EngineMode,
    ) -> Dict[str, Any]:
        """Run ARIA engine for one (task, model, mode) combination.

        Returns a dict with the prediction, latency, and metadata.
        Currently uses a placeholder for the engine invocation; in
        production this calls :meth:`ARIAEngine.forward_predict`.
        """
        try:
            from aria import ARIAEngine
            engine = ARIAEngine(kg=self.kg, model=model, mode=mode.value)
            result: ARIAResult = engine.forward_predict(
                material=task.get("query", {}).get("material", "unknown"),
                processing=task.get("query", {}).get("processing", {}),
                target_property=task.get("query", {}).get("target_property", ""),
            )
            prediction = result.to_dict()
            latency = result.latency_ms
        except (ImportError, Exception) as exc:
            logger.warning(
                "Engine call failed (model=%s, mode=%s): %s -- using empty prediction",
                model, mode.value, exc,
            )
            prediction = {}
            latency = 0.0

        return {
            "task_id": task.get("id", ""),
            "model": model,
            "mode": mode.value,
            "prediction": prediction,
            "latency_ms": latency,
        }

    # -- main run -----------------------------------------------------------

    def run(
        self,
        task_file: str,
        output_dir: str = "benchmark_results",
    ) -> pd.DataFrame:
        """Run all engine modes on tasks and compute metrics.

        Parameters
        ----------
        task_file :
            Path to a JSONL file of benchmark tasks.
        output_dir :
            Directory to write results and metrics.

        Returns
        -------
        pd.DataFrame
            One row per (task, model, mode) with metric columns.
        """
        tasks = self.load_tasks(task_file)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        metrics_computer = MetricsComputer(kg=self.kg)
        rows: List[Dict[str, Any]] = []

        for task in tasks:
            ground_truth = task.get("ground_truth", {})
            for model in self.models:
                for mode in self.modes:
                    logger.info(
                        "Running task=%s model=%s mode=%s",
                        task.get("id"), model, mode.value,
                    )
                    start = time.perf_counter()
                    run_result = self._run_single(task, model, mode)
                    elapsed = (time.perf_counter() - start) * 1000

                    prediction = run_result["prediction"]

                    # Compute metrics
                    metric_scores = metrics_computer.compute_all(prediction, ground_truth)

                    row = {
                        "task_id": run_result["task_id"],
                        "model": run_result["model"],
                        "mode": run_result["mode"],
                        "latency_ms": elapsed,
                        **metric_scores,
                    }
                    rows.append(row)

        df = pd.DataFrame(rows)

        # Save results
        df.to_csv(out_path / "benchmark_results.csv", index=False)
        df.to_json(out_path / "benchmark_results.json", orient="records", indent=2)
        logger.info("Benchmark complete: %d rows saved to %s", len(df), out_path)
        return df

    # -- comparison ---------------------------------------------------------

    @staticmethod
    def compare(results: pd.DataFrame) -> pd.DataFrame:
        """Produce a comparison table grouped by model and mode.

        Aggregates all numeric metric columns using mean and includes
        standard deviation where possible.
        """
        numeric_cols = results.select_dtypes(include=[np.number]).columns.tolist()
        if "task_id" in numeric_cols:
            numeric_cols.remove("task_id")

        group_cols = [c for c in ("model", "mode") if c in results.columns]
        if not group_cols:
            return results

        agg_dict = {col: ["mean", "std"] for col in numeric_cols}
        comparison = results.groupby(group_cols).agg(agg_dict)
        comparison.columns = [
            f"{col}_{stat}" for col, stat in comparison.columns
        ]
        comparison = comparison.reset_index()
        return comparison


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """``aria-benchmark`` command-line entry point."""
    parser = argparse.ArgumentParser(
        description="ARIA Benchmark Runner",
        prog="aria-benchmark",
    )
    parser.add_argument(
        "task_file",
        help="Path to JSONL benchmark tasks file",
    )
    parser.add_argument(
        "--kg-file",
        help="Path to KG JSON file (optional)",
        default=None,
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["qwen2:7b"],
        help="Model identifiers to test",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=[m.value for m in EngineMode],
        help="Engine modes to test",
    )
    parser.add_argument(
        "--output-dir",
        default="benchmark_results",
        help="Directory to write results",
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
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Load KG if provided
    kg = None
    if args.kg_file:
        from aria.kg.graph_store import load_kg
        kg = load_kg(args.kg_file)

    modes = [EngineMode(m) for m in args.modes]

    runner = BenchmarkRunner(kg=kg, models=args.models, modes=modes)
    results_df = runner.run(args.task_file, args.output_dir)

    # Print comparison
    comparison = BenchmarkRunner.compare(results_df)
    print("\n=== Benchmark Comparison ===\n")
    print(comparison.to_string(index=False))

    # Optional LLM Judge
    if args.judge:
        judge = LLMJudge(backend=args.judge_backend, model=args.models[0])
        tasks = BenchmarkRunner.load_tasks(args.task_file)

        judge_results = []
        for task in tasks:
            query = task.get("query", {})
            ground_truth = task.get("ground_truth", {})
            # Get the ARIA prediction from the results DataFrame
            row = results_df[
                (results_df["task_id"] == task.get("id", "")) &
                (results_df["model"] == args.models[0]) &
                (results_df["mode"] == modes[0].value)
            ]
            prediction = row.iloc[0].to_dict() if len(row) > 0 else {}

            result = judge.evaluate_all_metrics(query, prediction, ground_truth)
            judge_results.append(result)

        from aria.evaluation.judge import create_judge_report
        summary = create_judge_report(
            judge_results,
            str(Path(args.output_dir) / "judge_report.txt"),
        )
        print("\n=== Judge Summary ===\n")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()