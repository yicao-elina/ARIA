# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ARIA (Causal-Aware Reasoning for Intelligent Analysis) is a causal evidence-gating framework for materials science. Unlike standard RAG, ARIA determines *when* retrieved evidence is *causally sufficient* for scientific decision-making by tracing Processing-Structure-Property (PSP) pathways in a knowledge graph. It targets 2D electronic materials (TMDs like MoS2, WS2, WSe2).

## Commands

```bash
make install          # Install package (editable)
make install-dev      # Install with dev dependencies (pytest, ruff, mypy)
make install-all      # Install with all optional deps (openai, spacy, viz, dev)
make test             # Run all tests
make test-cov         # Run tests with coverage report
make lint             # Ruff check + mypy type check
make format           # Ruff format
make benchmark         # Run forward + inverse benchmark tasks
make clean            # Remove build artifacts
```

Run a single test file or test:
```bash
python -m pytest tests/test_types.py -v
python -m pytest tests/test_kg.py::test_load_kg -v
```

Skip slow/integration tests (which require Ollama running):
```bash
python -m pytest tests/ -v -k "not slow"
```

CLI entry points after install:
```bash
aria-benchmark    # aria.evaluation.benchmark:main
aria-diagnose     # aria.kg.diagnostics:main
```

## Architecture

### Three-Tier Causal Cascade (core design)

The `ReasoningRouter` (`aria/reasoning/router.py`) dispatches queries through three tiers:

1. **Tier 1 (DIRECT)** — Exact PSP path match in KG. If query keywords match KG nodes and paths exist, use them with LLM generation.
2. **Tier 2 (ANALOGICAL)** — Sentence-transformer embeddings find the most semantically similar KG node; its causal pathways are adapted. Falls back if similarity is below threshold.
3. **Tier 3 (FALLBACK)** — Pure LLM reasoning with no KG evidence. Also used as the baseline mode for ablation studies.

### Five Engine Modes

`ARIAEngine` (`aria/engine.py`, ~860 lines) supports five modes via `EngineMode` enum:

| Mode | Behavior |
|------|----------|
| `baseline` | Pure LLM, no KG |
| `naive_kg` | Simple KG + LLM concatenation (ablation control) |
| `aria` | Three-tier causal cascade (default) |
| `aria_search` | Three-tier + OpenAlex/Semantic Scholar literature search |
| `aria_full` | Three-tier + literature + chain-of-thought transparency |

All modes return the same `ARIAResult` dataclass (`aria/types.py`), enabling consistent evaluation across modes.

### Module Map

```
aria/
├── types.py            # Core data types (ARIAResult, ReasoningTier, EngineMode, PSPRelationship, etc.)
├── engine.py           # ARIAEngine — unified entry point, ~860 lines, dispatches to 5 modes
├── kg/
│   ├── graph_store.py  # NetworkX DiGraph storage, load/save KG, path search
│   ├── schema.py       # PSP node/edge classification, schema validation
│   └── diagnostics.py # KG health checks and statistics
├── reasoning/
│   ├── router.py       # ReasoningRouter — tier dispatch logic
│   ├── tier1_direct.py # Direct path matching
│   ├── tier2_analogical.py # Similarity-based transfer
│   ├── tier3_fallback.py   # Pure LLM fallback
│   ├── prompts.py      # LLM prompt templates for each tier
│   └── literature.py   # OpenAlex/Semantic Scholar API client
├── retrieval/
│   ├── path_search.py  # PSP path finding in KG
│   ├── similarity.py   # Node embedding similarity (sentence-transformers)
│   ├── completeness.py # Causal completeness scoring: C(E,q) = |L(E) ∩ L_req(q)| / |L_req(q)|
│   └── evidence_ranker.py # Composite ranking (confidence 0.35, richness 0.30, PSP coverage 0.35)
├── llm/
│   ├── client.py       # LLM client abstraction (Ollama subprocess, OpenAI stub)
│   └── embeddings.py   # Sentence-transformer embedding wrapper
├── evaluation/
│   ├── metrics.py      # MetricsComputer (causal_coherence, source_grounding, etc.)
│   ├── benchmark.py    # BenchmarkRunner, task loading, CLI entry point
│   └── judge.py        # LLM-as-judge evaluation
├── visualization/
│   ├── graph_viz.py    # KG graph visualization
│   ├── trace_viz.py    # Causal trace visualization
│   └── jhu_theme.py   # JHU color palette for matplotlib
└── materials/
    ├── psp.py          # PSP layer classification (keyword-based)
    ├── constraints.py  # Physical validation for 2D materials
    └── units.py        # Unit parsing and conversion
```

### Data Flow

```
Query → ReasoningRouter → (Tier 1/2/3) → LLM generation → ARIAResult
                             ↑                    |
                    KG path search         Evidence ranking
                    Node similarity        Completeness check
                    (Optional: literature search)
```

### Key Design Patterns

- **Lazy imports** in `__init__.py` — `ARIAEngine`, `load_kg`, `save_kg` loaded on demand to avoid importing heavy deps (sentence-transformers, networkx) at module level
- **Unified output type** — `ARIAResult` is the single return type across all modes
- **PSP classification via keyword matching** — extensible keyword sets in `types.py` (`_infer_psp_type`) and `materials/psp.py`
- **Composite evidence ranking** — weighted score: confidence (0.35) + evidence richness (0.30) + PSP coverage (0.35)
- **Physical constraints** — `materials/constraints.py` validates temperature ranges, precursor-substrate compatibility, atmosphere-dopant compatibility for 2D materials

### Knowledge Graph

- Full KG: `data/aria_2d_kg_v1.json` (421 relationships, 777 nodes) — gitignored due to size
- Demo KG: `data/aria_2d_kg_demo.json` (27 relationships, 34 nodes) — curated for tutorial with complete P→S→P chains, P→P shortcuts (contextual tunneling), and WS2 analogical transfer edges
- Tiny KG: `data/aria_2d_kg_tiny.json` (6 curated relationships) — in repo, used for tests
- Benchmarks: `data/benchmarks/{forward_prediction,inverse_design,ood_generalization}.jsonl`
- See `data/KG_PIPELINE.md` for KG construction pipeline details
- **Critical format note:** `load_kg()` reads `cause_parameter` and `effect_on_doping` as node identifiers (lines 77-78 of `aria/kg/graph_store.py`). These fields MUST be present in KG JSON or edges are silently skipped.

### Skills and Agents

Skills in `.claude/skills/` and orchestrator in `.claude/agents/`:
- `kg-builder` — Build/extend PSP KGs from PDFs or keyword-based literature search (OpenAlex/Semantic Scholar)
- `aria-setup` — Install dependencies, configure .env, load KG, initialize ARIAEngine
- `aria-run` — Run forward_predict/inverse_design, format results as synthesis reports
- `aria-evaluate` — Compute metrics (MetricsComputer), run benchmarks, LLM-as-judge evaluation
- `orchestrator` — Coordinates the full workflow (setup → kg-builder → run → evaluate), tracks environment state

### Tutorial Notebooks

- `examples/05_end_to_end_tutorial.ipynb` — Comprehensive end-to-end walkthrough covering KG exploration, contextual tunneling demonstration, ARIA recovery, performance evaluation, and material synthesis reports. Works without Ollama (mock mode) or with Ollama (live mode).
- `examples/01_build_psp_kg.ipynb` through `04_causal_traces_and_evaluation.ipynb` — Focused tutorials on specific features

### LLM Configuration

Configure via `.env` file (see `.env.example`):
- `LLM_BACKEND`: `ollama` (default) or `openai`
- `LLM_MODEL`: default `qwen2:7b`
- `EMBEDDING_MODEL`: default `all-MiniLM-L6-v2`
- `SEARCH_EMAIL`: for OpenAlex/Semantic Scholar APIs

## Style and Conventions

- Python 3.9+ compatibility required
- Ruff formatting with line length 100
- All modules use type hints; `mypy --ignore-missing-imports` for type checking
- Test fixtures in `tests/conftest.py` use a tiny KG mock; sentence-transformer tests have `@pytest.mark.slow` skip markers
- Dataclasses use `to_dict()` for serialization; `from_legacy()` classmethods for backward-compatible format conversion