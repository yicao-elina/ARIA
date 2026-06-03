#!/usr/bin/env python3
"""ARIA Benchmark Runner CLI.

Run forward prediction, inverse design, and OOD generalization
benchmarks against the ARIA engine modes.

Usage:
    python scripts/run_benchmark.py --task forward_prediction --kg data/aria_2d_kg_v1.json
    python scripts/run_benchmark.py --task inverse_design --kg data/aria_2d_kg_tiny.json --model qwen2:7b
    python scripts/run_benchmark.py --task all --output-dir benchmark_results -v
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the aria package is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from aria.evaluation.benchmark import BenchmarkRunner
from aria.types import EngineMode

logger = logging.getLogger(__name__)

BENCHMARK_DIR = PROJECT_ROOT / "data" / "benchmarks"

TASK_FILES = {
    "forward_prediction": BENCHMARK_DIR / "forward_prediction.jsonl",
    "inverse_design": BENCHMARK_DIR / "inverse_design.jsonl",
    "ood_generalization": BENCHMARK_DIR / "ood_generalization.jsonl",
}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file into a list of dicts."""
    items = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed line %d in %s", line_num, path)
    return items


def run_single_task(
    task: Dict[str, Any],
    kg_path: Optional[str],
    model: str,
    mode: str,
) -> Dict[str, Any]:
    """Run a single benchmark task through the ARIA engine."""
    try:
        from aria import ARIAEngine, load_kg

        kg = load_kg(kg_path) if kg_path else None
        engine = ARIAEngine(kg=kg, model=model, mode=mode)

        if task.get("task") == "forward_prediction" or "fp_" in task.get("id", ""):
            result = engine.forward_predict(
                material=task.get("input", {}).get("material", ""),
                processing=task.get("input", {}).get("processing_conditions", {}),
                target_property=task.get("target_property", ""),
            )
        elif task.get("task") == "inverse_design" or "id_" in task.get("id", ""):
            # Inverse design uses the same engine with different parameters
            result = engine.forward_predict(
                material=task.get("target_material", ""),
                processing={},
                target_property=task.get("target_property", ""),
            )
        else:
            result = engine.forward_predict(
                material=task.get("input", {}).get("material", ""),
                processing=task.get("input", {}).get("processing_conditions", {}),
                target_property=task.get("target_property", ""),
            )

        return {
            "task_id": task.get("id", ""),
            "model": model,
            "mode": mode,
            "prediction": result.to_dict(),
            "tier": result.tier.value,
            "confidence": result.confidence,
            "latency_ms": result.latency_ms,
        }

    except Exception as exc:
        logger.warning("Engine call failed: %s -- using empty prediction", exc)
        return {
            "task_id": task.get("id", ""),
            "model": model,
            "mode": mode,
            "prediction": {},
            "tier": 3,
            "confidence": 0.0,
            "latency_ms": 0.0,
            "error": str(exc),
        }


def main():
    parser = argparse.ArgumentParser(
        description="ARIA Benchmark Runner",
        prog="aria-benchmark",
    )
    parser.add_argument(
        "--task",
        choices=["forward_prediction", "inverse_design", "ood_generalization", "all"],
        default="all",
        help="Which benchmark task file to run",
    )
    parser.add_argument(
        "--kg-file",
        type=str,
        default=str(PROJECT_ROOT / "data" / "aria_2d_kg_v1.json"),
        help="Path to KG JSON file",
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
        default=["baseline", "naive_kg", "aria"],
        help="Engine modes to test",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
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

    # Determine which tasks to run
    if args.task == "all":
        task_files = list(TASK_FILES.items())
    else:
        task_files = [(args.task, TASK_FILES[args.task])]

    modes = [EngineMode(m) for m in args.modes]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results: List[Dict[str, Any]] = []

    for task_name, task_path in task_files:
        if not task_path.exists():
            logger.error("Task file not found: %s", task_path)
            continue

        logger.info("Loading tasks from %s", task_path)
        tasks = load_jsonl(task_path)
        logger.info("Loaded %d %s tasks", len(tasks), task_name)

        for task in tasks:
            for model in args.models:
                for mode in modes:
                    logger.info(
                        "Running task=%s model=%s mode=%s",
                        task.get("id", "?"), model, mode.value,
                    )
                    start = time.perf_counter()
                    result = run_single_task(task, args.kg_file, model, mode.value)
                    elapsed = (time.perf_counter() - start) * 1000
                    result["wall_time_ms"] = elapsed
                    all_results.append(result)

        # Save per-task results
        task_results_path = output_dir / f"{task_name}_results.json"
        with open(task_results_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d results to %s", len(all_results), task_results_path)

    # Save combined results
    combined_path = output_dir / "all_benchmark_results.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    logger.info("Total results: %d", len(all_results))

    # Print summary
    print("\n=== Benchmark Summary ===")
    print(f"Tasks run: {len(all_results)}")
    for task_name, _ in task_files:
        task_count = sum(1 for r in all_results if task_name in r.get("task_id", ""))
        print(f"  {task_name}: {task_count} results")
    print(f"\nResults saved to: {output_dir}")
    print(f"Combined file: {combined_path}")


if __name__ == "__main__":
    main()