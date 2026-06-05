<div align="center">

<img src="docs/figures/ARIA-logo.svg" alt="ARIA Logo" width="180"/>

# ARIA: Causal-Aware Reasoning for Materials Discovery

**A**utonomous **R**easoning **I**ntelligence for **A**tomics

[![Paper](https://img.shields.io/badge/KDD_2026-Paper-blue)](https://github.com/yicao-elina/ARIA)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)

*When knowledge hurts — and how causal completeness rescues reasoning*

</div>

---

## Why ARIA?

More knowledge isn't always better. When you feed a language model everything a knowledge graph knows about a material, something counterintuitive happens: **performance drops**.

> 📉 Naive KG+LLM scores **lower** than the baseline LLM with no KG at all.  
> Forward prediction: 0.337 vs. 0.340. Interpretability: 0.350 vs. 0.877 — a **60% collapse**.

We call this failure mode **contextual tunneling**: the model over-anchors on narrow, factually-correct but *causally incomplete* evidence, suppressing its own broader physical reasoning. A P→P shortcut like *"CVD temperature increases carrier mobility"* is true — but it skips the *structural mediator* (crystallinity) that explains *why*. The LLM gloms onto the shortcut and stops thinking.

**ARIA fixes this** by gating evidence activation on **causal completeness** — not retrieval confidence. It only lets KG evidence through when it forms a complete Processing → Structure → Property chain. Otherwise, it honestly falls back to parametric reasoning rather than misleading you with half-truths.

<div align="center">
<img src="docs/figures/KDD-Fig1.pdf" alt="ARIA architecture: three-tier causal cascade" width="700"/>
<p><em>ARIA's three-tier causal cascade. Evidence is activated only when causally complete (Tier 1), transferred from analogs with physical checks (Tier 2), or explicitly flagged as ungrounded (Tier 3).</em></p>
</div>

## The Key Idea in 30 Seconds

| Standard RAG | ARIA |
|:---|:---|
| Retrieve everything that matches | Retrieve only what forms a **complete causal chain** |
| "More context is better" | "Causally incomplete context can *harm* reasoning" |
| No completeness check | PSP-Complete criterion: C(E,q) = \|L(E) ∩ L_req(q)\| / \|L_req(q)\| |
| One-size-fits-all prompting | Three-tier adaptive routing |

A PSP-complete path spans all required layers — Processing, Structure, Property. If you only have Processing → Property (a shortcut), you're missing the *mechanism*. ARIA detects this and handles it differently.

## Results

| System | Forward (ID) | Inverse (ID) | Interpretability |
|:---|:---:|:---:|:---:|
| Baseline LLM | 0.340 | 0.326 | 0.877 |
| Naive KG+LLM | 0.337 ↓ | 0.285 ↓ | 0.350 ↓↓ |
| **ARIA-CORE** | **0.410** ↑ | **0.377** ↑ | **0.833** ↑ |
| **ARIA-FULL** | **0.512** ↑↑ | **0.498** ↑↑ | **0.912** ↑↑ |

- **ARIA-CORE** recovers the naive KG deficit and then some: **+21.6% over naive** forward, **+32.6% over naive** inverse.
- **ARIA-FULL** with literature search achieves **+53.8% over baseline** on forward prediction.
- **Interpretability**: Naive KG collapses to 0.350; ARIA restores it to 0.833–0.912.

<div align="center">
<img src="docs/figures/KDD_Fig4.pdf" alt="ARIA performance comparison across tiers" width="700"/>
<p><em>Tier-specific performance. ARIA's selective evidence activation prevents contextual tunneling while naive KG amplifies it.</em></p>
</div>

## How It Works

<div align="center">
<img src="docs/figures/KDD_Fig3-KG-workflow.pdf" alt="Knowledge graph construction pipeline" width="700"/>
<p><em>CKG construction pipeline: from literature to PSP relationships.</em></p>
</div>

### The Three Tiers

1. **Tier 1 — DIRECT** 🎯  
   PSP-complete path found in the KG. Example: *"CVD at 750°C → increased crystallinity → higher carrier mobility"*.  
   The LLM receives the full causal chain and generates a grounded prediction with high confidence.

2. **Tier 2 — ANALOGICAL** 🔄  
   No direct path, but a *similar material* has one. Example: *"WS₂ is structurally similar to MoS₂; we transfer its crystallinity → mobility pathway with physical feasibility checks."*  
   Confidence is discounted, and a disclaimer is prepended.

3. **Tier 3 — FALLBACK** 🔦  
   No KG evidence at all. The LLM reasons from parametric knowledge alone, and the output is *explicitly flagged* as ungrounded.  
   This is epistemically honest: "I don't have verified evidence, so here's my best guess with low confidence."

### Why Naive KG Makes Things Worse

Naive KG+LLM concatenates *all* retrieved paths into the prompt — shortcuts and complete chains alike. The LLM then over-anchors on the shortcut (which is shorter, more salient, and factually correct) while suppressing its own ability to reason about the missing structural mediator. This is **contextual tunneling**: factually accurate evidence that forms an *incomplete* causal chain.

ARIA prevents this by checking PSP-completeness *at inference time* — not at retrieval time. If the evidence doesn't span all required layers, it doesn't go into the prompt.

## Installation

```bash
pip install aria-materials
```

For development with all optional dependencies:
```bash
pip install -e ".[all]"
```

### Optional: Install Ollama for local LLM inference

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b
```

## Quick Start

```python
from aria import ARIAEngine, load_kg

# Load the demo knowledge graph (27 PSP relationships, MoS₂ and WS₂)
kg = load_kg("data/aria_2d_kg_demo.json")

# Initialize the engine (default: three-tier causal cascade)
engine = ARIAEngine(kg=kg, model="qwen2:7b", mode="aria")

# Forward prediction: given synthesis conditions, predict properties
result = engine.forward_predict(
    material="MoS2",
    processing={"temperature": "750C", "method": "CVD"},
    target_property="carrier mobility"
)

print(f"Prediction: {result.answer}")
print(f"Tier: {result.tier.name}")           # DIRECT, ANALOGICAL, or FALLBACK
print(f"Confidence: {result.confidence:.2f}")
for step in result.causal_trace:
    print(f"  {step.processing} → {step.structure} → {step.property_}")
```

### See Contextual Tunneling in Action

The [end-to-end tutorial](examples/05_end_to_end_tutorial.ipynb) walks through:

1. **Loading the KG** and exploring PSP structure
2. **Running all modes** (baseline, naive_kg, aria) on the same query
3. **Seeing naive KG fail** — the P→P shortcut "CVD 750°C → carrier mobility" bypasses crystallinity, causing the LLM to over-anchor
4. **Seeing ARIA recover** — Tier 1 activates the complete P→S→P chain, restoring mechanistic reasoning
5. **Evaluating performance** with causal coherence and interpretability metrics

## Modes

| Mode | Description | When to use |
|:-----|:-----------|:-----------|
| `baseline` | Pure LLM, no KG | Baseline comparison only |
| `naive_kg` | Simple KG+LLM concatenation | Ablation control — **expect worse results** |
| `aria` | Three-tier causal cascade | **Default — recommended** |
| `aria_search` | + literature search (OpenAlex, Semantic Scholar) | Need external validation & citations |
| `aria_full` | + chain-of-thought transparency | Full provenance tracking |

## Knowledge Graph

### Demo KG (`data/aria_2d_kg_demo.json`)

A curated **27-relationship** KG designed for the tutorial, featuring:

- **Complete P→S→P chains** for MoS₂ (CVD 750°C → crystallinity → carrier mobility)
- **P→P shortcuts** that cause contextual tunneling (CVD 750°C → carrier mobility, bypassing structure)
- **WS₂ analogical transfer** edges (enables Tier 2)
- **Orphan edges** (partial evidence, demonstrates incompleteness)

### Full KG (`data/aria_2d_kg_v1.json`)

421 causal relationships over 777 nodes covering 2D electronic materials (MoS₂, WS₂, WSe₂, MoSe₂, etc.). Gitignored due to size — generate via `scripts/build_kg.py`.

### PSP Edge Schema

```json
{
  "cause_parameter": "CVD temperature 750C",
  "effect_on_doping": "crystallinity",
  "affected_property": "crystallinity",
  "mechanism_quote": "CVD growth at 750C yields large-grain MoS2 with improved crystallinity",
  "source_file": "demo_MoS2_synthesis",
  "confidence_level": "high",
  "source": "CVD temperature 750C",
  "relation": "increases",
  "target": "crystallinity",
  "psp_type": "Processing_to_Structure",
  "material": "MoS2",
  "confidence": 0.90,
  "curation": "expert_verified",
  "relationship_id": "demo_rel_1"
}
```

> ⚠️ **Format note**: `load_kg()` requires `cause_parameter` and `effect_on_doping` fields — these become graph node names. Always include them for compatibility.

## Tutorials

| Notebook | Description |
|:---------|:-----------|
| [01_build_psp_kg.ipynb](examples/01_build_psp_kg.ipynb) | Building and exploring PSP knowledge graphs |
| [02_forward_prediction.ipynb](examples/02_forward_prediction.ipynb) | Forward prediction with ARIA |
| [03_inverse_design.ipynb](examples/03_inverse_design.ipynb) | Inverse synthesis design |
| [04_causal_traces_and_evaluation.ipynb](examples/04_causal_traces_and_evaluation.ipynb) | Causal traces, completeness & evaluation |
| **[05_end_to_end_tutorial.ipynb](examples/05_end_to_end_tutorial.ipynb)** | **Full walkthrough: contextual tunneling demo, ARIA recovery, evaluation** |

## Build Your Own KG

Use the **kg-builder** skill (for Claude Code) to construct a PSP knowledge graph from PDFs or keyword-based literature search:

```
/kg-builder   # Build KG from PDFs or Semantic Scholar keywords
/aria-setup   # Configure environment, load KG, initialize engine
/aria-run     # Run forward prediction or inverse design
/aria-evaluate # Compute metrics, compare modes, LLM-judge scoring
```

Or programmatically:

```python
from aria.reasoning.literature import LiteratureSearcher

# Search for papers
searcher = LiteratureSearcher(email="your_email@institution.edu")
papers = searcher.search("CVD MoS2 synthesis carrier mobility", max_results=10)

# Extract PSP relationships and build your KG
from aria.types import PSPRelationship
from aria.kg.graph_store import save_kg

# ... extract and normalize relationships ...
save_kg(your_graph, "data/my_custom_kg.json")
```

## Reproduce Paper Results

```bash
pip install aria-materials
python scripts/run_benchmark.py --model qwen2:7b --task forward
python scripts/run_benchmark.py --model qwen2:7b --task inverse
python scripts/run_benchmark.py --model qwen2:7b --task ood
```

## Honest Limitations

ARIA is not a silver bullet. The paper identifies important caveats:

- **KG coverage dependency**: Tier 1 only activates for queries with PSP-complete paths in the KG. For our CKG, that's 62.5% of forward queries and 0% of inverse queries.
- **Inverse design bottleneck**: The CKG's P→S→P orientation creates a 3.4× forward/reverse reachability asymmetry, making inverse design primarily a Tier 3 task.
- **ARIA-CORE HC2 < baseline HC2**: For stoichiometric parameters specifically, ARIA-CORE (0.360) underperforms baseline (0.390) because Tier 1 retrieves causal paths without explicit stoichiometric detail.
- **Scope**: Evaluated on 2D doped materials (MoS₂, WS₂, WSe₂, MoSe₂, etc.). Extending to other domains requires a new domain-specific CKG.

## Relationship to LLM4Chem

This project builds on our earlier work from the [LLM4Chem hackathon](https://github.com/yicao-elina/LLM4Chem-Explainable-synthesis). ARIA represents a fundamental redesign: rather than naively injecting knowledge graph context into LLM prompts, ARIA gates evidence on causal completeness, preventing the contextual tunneling failure mode we identified in the LLM4Chem experiments. The PSP hierarchy and knowledge graph schema are evolved from that initial prototype.

## Citation

```bibtex
@inproceedings{aria2026,
  title={When Knowledge Hurts: Causal-Aware Reasoning for Materials Discovery},
  author={Cao, Yi and Wang, Liaoyaqi and Chen, Jieneng and others},
  booktitle={Proceedings of the 32nd ACM SIGKDD Conference on Knowledge Discovery and Data Mining (KDD '26)},
  year={2026},
  organization={ACM}
}
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.