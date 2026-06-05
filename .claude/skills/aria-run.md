# ARIA Predictions

Run forward predictions and inverse design using the ARIA engine.

## Activation

When the user asks to run a prediction, perform inference, do forward prediction, do inverse design, or mentions "aria-run", "run ARIA", "predict property", "design synthesis conditions", or "forward_predict" / "inverse_design".

## Prerequisites

Ensure the engine is initialized (see aria-setup skill):

```python
from aria import ARIAEngine, load_kg

kg = load_kg("data/aria_2d_kg_demo.json")
engine = ARIAEngine(kg=kg, model="qwen2:7b", mode="aria")
```

## Forward Prediction

Predict a material property given processing conditions:

```python
result = engine.forward_predict(
    material="MoS2",
    processing={"temperature": "750C", "method": "CVD", "atmosphere": "Ar"},
    target_property="carrier mobility",
)
```

Parameters:
- `material` -- Material name (e.g. `"MoS2"`, `"WS2"`, `"WSe2"`)
- `processing` -- Dict of processing conditions (temperature, method, atmosphere, substrate, etc.)
- `target_property` -- Property to predict (e.g. `"carrier mobility"`, `"band gap"`, `"photoluminescence"`)

## Inverse Design

Suggest processing conditions to achieve a target property:

```python
result = engine.inverse_design(
    target_material="MoS2",
    target_property="high n-type mobility",
    constraints={"method": "CVD"},
)
```

Parameters:
- `target_material` -- Material to design for
- `target_property` -- Desired property outcome
- `constraints` -- Optional dict of fixed constraints (e.g. synthesis method, substrate)

## Understanding the Result

Both methods return an `ARIAResult` dataclass:

```python
result.answer              # Dict[str, Any] -- the core prediction
result.tier                # ReasoningTier enum: DIRECT(1), ANALOGICAL(2), FALLBACK(3)
result.confidence          # float 0.0--1.0
result.reasoning_type      # str: "direct_path", "transfer_learning", "baseline_fallback", etc.
result.causal_trace        # List[CausalTraceStep] -- PSP chain steps
result.missing_evidence    # List[str] -- what evidence was unavailable
result.kg_paths_used       # int -- number of KG paths used
result.kg_paths            # List[str] -- human-readable path descriptions
result.literature_papers    # List[Dict] -- papers found (aria_search/aria_full only)
result.mode                # str -- engine mode used
result.model               # str -- LLM model name
result.latency_ms          # float -- inference time in milliseconds
```

### ReasoningTier values

```python
from aria.types import ReasoningTier

ReasoningTier.DIRECT      # 1 -- exact PSP path match in KG
ReasoningTier.ANALOGICAL  # 2 -- similarity-based analogical transfer
ReasoningTier.FALLBACK    # 3 -- pure LLM reasoning, no KG evidence
```

A result with `tier=ReasoningTier.DIRECT` means the KG had a matching causal pathway. `FALLBACK` means the answer is entirely from the LLM with no KG grounding.

### Serialization

```python
result_dict = result.to_dict()    # Python dict
result_json = result.to_json()     # JSON string
```

Use these for saving results to disk or logging.

## Physical Constraint Validation

Before trusting inverse design results, validate synthesis conditions:

```python
from aria.materials.constraints import validate_synthesis_conditions

conditions = {"temperature": 750, "method": "CVD", "material": "MoS2"}
validation = validate_synthesis_conditions(conditions)
# Returns dict of constraint checks, e.g.:
# {"temperature_range": True, "substrate_compatibility": True, ...}
```

Always check validation results and flag any `False` entries to the user.

## Visualization

### Causal trace diagram

```python
from aria.visualization.trace_viz import plot_causal_trace

plot_causal_trace(result, output_path="outputs/causal_trace.png")
```

Renders a Processing -> Structure -> Property chain diagram with JHU-themed colors.

### Tier comparison across modes

```python
from aria.visualization.trace_viz import plot_tier_comparison

# Compare results from different engine modes
results = [baseline_result, aria_result, aria_full_result]
plot_tier_comparison(results, output_path="outputs/tier_comparison.png")
```

## Mode Selection Guide

| Use case | Recommended mode |
|----------|-----------------|
| Quick baseline comparison | `"baseline"` |
| Simple KG-augmented generation | `"naive_kg"` |
| Production predictions | `"aria"` |
| Predictions with literature grounding | `"aria_search"` |
| Full transparency with chain-of-thought | `"aria_full"` |

To run the same query across multiple modes for comparison:

```python
from aria.types import EngineMode

modes = ["baseline", "naive_kg", "aria", "aria_search", "aria_full"]
results = {}
for mode in modes:
    engine = ARIAEngine(kg=kg, model="qwen2:7b", mode=mode)
    result = engine.forward_predict(material="MoS2", processing={"temperature": "750C"}, target_property="carrier mobility")
    results[mode] = result
```

## Batch Predictions

For multiple queries, loop and collect results:

```python
queries = [
    {"material": "MoS2", "processing": {"temperature": "750C"}, "target_property": "carrier mobility"},
    {"material": "WS2", "processing": {"temperature": "900C"}, "target_property": "band gap"},
]
results = []
for q in queries:
    r = engine.forward_predict(**q)
    results.append(r)
    print(f"{q['material']}: tier={r.tier.name}, conf={r.confidence:.2f}")
```