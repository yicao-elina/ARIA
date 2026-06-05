# ARIA Evaluation

Evaluate ARIA predictions using metrics, benchmarks, and LLM-as-judge scoring.

## Activation

When the user asks to evaluate, benchmark, score, or assess ARIA results, or mentions "aria-evaluate", "metrics", "benchmark", "judge", "evaluation", or "compare modes".

## Metrics Computation

### Initialize the metrics computer

```python
from aria.evaluation.metrics import MetricsComputer
from aria import load_kg

kg = load_kg("data/aria_2d_kg_demo.json")
computer = MetricsComputer(kg=kg)
```

### Individual metrics

```python
# Causal coherence: does the output trace a coherent PSP causal chain?
score = computer.causal_coherence(output=result, ground_truth=gt)

# Source grounding: is the output grounded in KG/literature evidence?
score = computer.source_grounding(output=result, ground_truth=gt)

# Internal validity: are the claimed causal links internally consistent?
score = computer.internal_validity(output=result)

# PSP consistency: does the output respect Processing-Structure-Property ordering?
score = computer.psp_consistency(output=result)
```

Each metric returns a float between 0.0 and 1.0.

### Compute all metrics at once

```python
all_metrics = computer.compute_all(output=result, ground_truth=gt)
# Returns a dict: {"causal_coherence": ..., "source_grounding": ...,
#                  "internal_validity": ..., "psp_consistency": ...}
```

## Benchmark Runner

### Load and run benchmark tasks

```python
from aria.evaluation.benchmark import BenchmarkRunner
from aria import load_kg

kg = load_kg("data/aria_2d_kg_demo.json")
runner = BenchmarkRunner(kg=kg)

# Load tasks from JSONL file
tasks = BenchmarkRunner.load_tasks("data/benchmarks/forward_prediction.jsonl")

# Run all tasks and save results
runner.run(task_file="data/benchmarks/forward_prediction.jsonl", output_dir="outputs/benchmark_results")
```

Available benchmark task files:
- `data/benchmarks/forward_prediction.jsonl`
- `data/benchmarks/inverse_design.jsonl`
- `data/benchmarks/ood_generalization.jsonl`

Each task is a JSONL line with fields like `material`, `processing`, `target_property`, and `ground_truth`.

### Compare results across modes

```python
# Run with specific models and modes
runner = BenchmarkRunner(
    kg=kg,
    models=["qwen2:7b"],
    modes=["baseline", "aria", "aria_full"],
)

# Compare multiple result sets
comparison = BenchmarkRunner.compare(results_list)
# Returns a pandas DataFrame with metric averages per mode
```

## LLM-as-Judge Evaluation

### Initialize the judge

```python
from aria.evaluation.judge import LLMJudge

judge = LLMJudge()
```

The `LLMJudge` scores predictions on four domain-specific rubrics:

| Rubric | Max Score | What it measures |
|--------|-----------|-----------------|
| Processing Feasibility | 40 | Thermodynamic & kinetic viability of processing conditions |
| Structure Emergence | 30 | Correct prediction of structural outcomes |
| Property Consistency | 20 | Physical consistency of predicted properties |
| Causal PSP Reasoning | 10 | Quality of causal chain reasoning |

### Use the judge

```python
scores = judge.evaluate(prediction=result, ground_truth=gt)
# Returns rubric-level scores with explanations
```

## Full Evaluation Pipeline

A complete evaluation workflow:

1. Run predictions across all engine modes using the aria-run skill.
2. Compute automatic metrics with `MetricsComputer`.
3. Run benchmarks with `BenchmarkRunner`.
4. Optional: Get LLM-judge scores with `LLMJudge`.
5. Compare and visualize results:

```python
from aria.visualization.trace_viz import plot_tier_comparison

plot_tier_comparison(all_results, output_path="outputs/evaluation_comparison.png")
```

6. Save results to disk:

```python
import json
for mode, result in results.items():
    with open(f"outputs/{mode}_result.json", "w") as f:
        json.dump(result.to_dict(), f, indent=2)
```

## Interpreting Results

- **Tier distribution**: A healthy system should route most queries to DIRECT or ANALOGICAL tiers. A high FALLBACK rate indicates KG coverage gaps.
- **Confidence scores**: Compare confidence across modes. ARIA should show higher confidence than baseline for well-covered materials.
- **Causal coherence**: Should be >0.7 for DIRECT-tier predictions. Low coherence may indicate broken PSP chains.
- **PSP consistency**: Should approach 1.0. Values below 0.5 suggest the model is not respecting causal ordering.