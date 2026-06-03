# ARIA: Causal-Aware Reasoning for Materials Discovery

> **ARIA activates retrieved evidence only when it forms a causally complete PSP path.**
> More retrieval isn't always better — without causal completeness, evidence can harm reasoning.

ARIA is a causal evidence-gating framework that helps LLMs reason over **Processing–Structure–Property (PSP)** pathways for materials synthesis and property prediction. Unlike standard RAG, ARIA determines *when retrieved evidence is causally sufficient* for scientific decision-making.

## Architecture

```
Query: "How to synthesize MoS₂ with high mobility?"
                                    │
                        ┌───────────┴───────────┐
                        │   Causal Completeness  │
                        │       Check            │
                        └───────────┬───────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
         ┌──────┴──────┐    ┌──────┴──────┐    ┌──────┴──────┐
         │   Tier 1    │    │   Tier 2    │    │   Tier 3    │
         │   Direct    │    │ Analogical  │    │  Fallback   │
         │  PSP-Complete│    │  Transfer   │    │  Parametric │
         │   Path       │    │  (similar   │    │  LLM only   │
         │              │    │   systems)  │    │  + uncertainty│
         └──────────────┘    └─────────────┘    └─────────────┘
                │                   │                   │
         ┌──────┴─────────────────┴───────────────────┴──────┐
         │              ARIAResult:                           │
         │   answer | tier | confidence | causal_trace       │
         │   missing_evidence | kg_paths | literature_papers │
         └───────────────────────────────────────────────────┘
```

## Installation

```bash
pip install aria-materials
```

For development:
```bash
pip install -e ".[dev]"
```

### Optional: Install Ollama for local LLM inference

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b
```

## Quick Start

```python
from aria import ARIAEngine, load_kg

# Load the knowledge graph
kg = load_kg("data/aria_2d_kg_v1.json")

# Initialize the engine (default mode: 3-tier causal cascade)
engine = ARIAEngine(kg=kg, model="qwen2:7b", mode="aria")

# Forward prediction: given synthesis conditions, predict properties
result = engine.forward_predict(
    material="MoS2",
    processing={"temperature": "750C", "method": "CVD", "substrate": "SiO2/Si"},
    target_property="carrier mobility"
)

print(f"Prediction: {result.answer}")
print(f"Tier: {result.tier.name}")           # DIRECT, ANALOGICAL, or FALLBACK
print(f"Confidence: {result.confidence:.2f}")
print(f"Causal trace: {result.causal_trace}")
print(f"Missing evidence: {result.missing_evidence}")

# Inverse design: from target property to synthesis conditions
proposal = engine.inverse_design(
    target_material="WS2",
    target_property={"band_gap": "1.8-2.0 eV", "carrier_type": "n-type"},
    constraints={"method": "CVD", "max_temperature": "850C"}
)

print(f"Synthesis protocol: {proposal.answer}")
print(f"Required structure: {proposal.causal_trace}")
```

## Modes

| Mode | Description | When to use |
|------|-------------|-------------|
| `baseline` | Pure LLM (no KG) | Baseline comparison |
| `naive_kg` | Simple KG+LLM concatenation | Ablation study |
| `aria` | 3-tier causal cascade | **Default — recommended** |
| `aria_search` | + literature search (OpenAlex, Semantic Scholar) | Need external validation |
| `aria_full` | + chain-of-thought transparency | Full provenance tracking |

## Tutorials

| Notebook | Description |
|----------|-------------|
| [01_build_psp_kg.ipynb](examples/01_build_psp_kg.ipynb) | Building and exploring PSP knowledge graphs |
| [02_forward_prediction.ipynb](examples/02_forward_prediction.ipynb) | Forward prediction with ARIA |
| [03_inverse_design.ipynb](examples/03_inverse_design.ipynb) | Inverse synthesis design |
| [04_causal_traces_and_evaluation.ipynb](examples/04_causal_traces_and_evaluation.ipynb) | Causal traces, completeness & evaluation |

## Data

### ARIA-2D-KG-v1

The included knowledge graph contains **421 causal relationships** over **777 nodes** covering 2D electronic materials (TMDs: MoS₂, WS₂, WSe₂, MoSe₂, etc.).

Each edge follows the PSP schema:

```json
{
  "source": "growth temperature 750C",
  "relation": "increases",
  "target": "crystallinity",
  "psp_type": "Processing_to_Structure",
  "material": "MoS2",
  "evidence_text": "Higher temperature leads to larger grain sizes...",
  "paper_doi": "10.1038/...",
  "confidence": 0.87,
  "curation": "expert_verified"
}
```

### Benchmarks

- `forward_prediction.jsonl` — Forward PSP prediction tasks
- `inverse_design.jsonl` — Inverse synthesis design tasks
- `ood_generalization.jsonl` — Out-of-domain generalization tasks

## Reproduce Paper Results

```bash
pip install aria-materials
python scripts/run_benchmark.py --model qwen2:7b --task forward
python scripts/run_benchmark.py --model qwen2:7b --task inverse
python scripts/run_benchmark.py --model qwen2:7b --task ood
```

## Key Concepts

### Causal Completeness

A retrieved evidence set E is **PSP-complete** for a query q if it covers at least one directed path connecting the intervention variable and outcome variable through the required PSP layers:

```
C(E, q) = |L(E) ∩ L_req(q)| / |L_req(q)|
```

where L = {Processing, Structure, Property}.

### Contextual Tunneling

When evidence is **incomplete** (missing structure mediator, or processing-only evidence), the LLM may over-anchor on narrow fragments, suppressing broader physical reasoning. ARIA prevents this by:

1. **Tier 1**: Using evidence only when a PSP-complete path exists
2. **Tier 2**: Transferring from similar materials with feasibility constraints
3. **Tier 3**: Explicitly falling back to parametric knowledge with reduced confidence

## API Reference

See [docs/api.md](docs/api.md) for full API documentation.

### Core Classes

- `ARIAEngine` — Unified reasoning engine (all modes)
- `ARIAResult` — Standardized output with causal traces
- `ReasoningTier` — DIRECT / ANALOGICAL / FALLBACK
- `PSPRelationship` — KG edge schema
- `NodeMatcher` — Embedding-based node similarity
- `KGDiagnostics` — KG quality analysis

### Utility Functions

- `load_kg(path)` — Load KG from JSON
- `save_kg(graph, path)` — Save KG to JSON
- `kg_stats(graph)` — Get KG statistics
- `causal_completeness_score(graph, paths, query)` — Compute completeness
- `find_psp_paths(graph, start, end)` — Find PSP paths in KG

## Citation

```bibtex
@inproceedings{aria2026,
  title={When Knowledge Hurts: Causal-Aware Reasoning for Materials Discovery},
  author={ARIA Team},
  booktitle={Proceedings of KDD 2026},
  year={2026}
}
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

## Contact

For questions and feedback, please open an issue on GitHub.