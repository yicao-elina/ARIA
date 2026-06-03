# ARIA API Reference

**ARIA: Causal-Aware Reasoning for Materials Discovery**

---

## Top-Level Imports

```python
from aria import ARIAEngine, load_kg, save_kg
from aria import ARIAResult, CausalTraceStep, ChainOfThought, EngineMode
from aria import KnowledgeSource, PSPRelationship, PSPType, ReasoningStep, ReasoningTier
```

---

## Core Types

### `ARIAResult`

Unified output for all ARIA engine modes. Every mode (baseline, naive_kg, aria, aria_search, aria_full) returns this same structure.

| Field | Type | Description |
|-------|------|-------------|
| `answer` | `Dict[str, Any]` | Prediction result (properties for forward, synthesis conditions for inverse) |
| `tier` | `ReasoningTier` | Which reasoning tier was activated (DIRECT=1, ANALOGICAL=2, FALLBACK=3) |
| `confidence` | `float` | Prediction confidence in [0, 1] |
| `reasoning_type` | `str` | How the prediction was made (e.g., `"direct_path"`, `"transfer_learning"`, `"baseline_fallback"`) |
| `causal_trace` | `List[CausalTraceStep]` | Step-by-step PSP chain showing how the prediction was derived |
| `missing_evidence` | `List[str]` | PSP layers not covered by the retrieved evidence |
| `kg_paths_used` | `int` | Number of KG paths used in the prediction |
| `kg_paths` | `List[str]` | The actual path strings from the KG |
| `literature_papers` | `List[Dict]` | Papers found via literature search (aria_search/aria_full only) |
| `source_attribution` | `Dict[str, Any]` | Source attribution details (aria_full only) |
| `chain_of_thought` | `Optional[ChainOfThought]` | Full reasoning chain with source attribution (aria_full only) |
| `mode` | `str` | Engine mode used |
| `model` | `str` | LLM model used |
| `latency_ms` | `float` | Inference latency in milliseconds |

Methods:
- `to_dict() -> dict` -- Convert to a plain dictionary
- `to_json() -> str` -- Convert to a JSON string

### `CausalTraceStep`

Single step in a PSP causal chain.

| Field | Type | Description |
|-------|------|-------------|
| `processing` | `str` | Synthesis condition (e.g., `"CVD temperature 750C"`) |
| `structure` | `str` | Structural change (e.g., `"improved crystallinity"`) |
| `property_` | `str` | Resulting property (e.g., `"higher carrier mobility"`) |
| `evidence_text` | `Optional[str]` | Supporting evidence sentence |
| `evidence_doi` | `Optional[str]` | DOI of source paper |
| `confidence` | `float` | Edge confidence in [0, 1] |

### `ReasoningTier`

Enum for the three-tier reasoning cascade.

| Value | Name | Description |
|-------|------|-------------|
| `1` | `DIRECT` | Exact PSP path match in KG |
| `2` | `ANALOGICAL` | Similarity-based analogical transfer |
| `3` | `FALLBACK` | Pure LLM fallback (no KG evidence) |

### `EngineMode`

Enum for ARIA engine operating modes.

| Value | Name | Description |
|-------|------|-------------|
| `"baseline"` | `BASELINE` | Pure LLM (no KG) |
| `"naive_kg"` | `NAIVE_KG` | Simple KG + LLM concatenation |
| `"aria"` | `ARIA` | 3-tier causal cascade (default) |
| `"aria_search"` | `ARIA_SEARCH` | 3-tier + literature search |
| `"aria_full"` | `ARIA_FULL` | 3-tier + literature + CoT transparency |

### `PSPType`

PSP (Processing-Structure-Property) edge types.

| Value | Description |
|-------|-------------|
| `"Processing_to_Structure"` | Synthesis condition causes structural change |
| `"Structure_to_Property"` | Structural feature determines property |
| `"Processing_to_Property"` | Direct shortcut (skips Structure) |
| `"Structure_to_Structure"` | Structural feature influences another |
| `"Processing_to_Processing"` | Process parameter influences another |

### `PSPRelationship`

A single edge in the PSP causal knowledge graph.

| Field | Type | Description |
|-------|------|-------------|
| `source` | `str` | Cause node |
| `relation` | `str` | Relation type (e.g., `"increases"`, `"decreases"`) |
| `target` | `str` | Effect node |
| `psp_type` | `str` | PSPType value |
| `material` | `str` | Material name (e.g., `"MoS2"`) |
| `evidence_text` | `Optional[str]` | Supporting evidence sentence |
| `paper_doi` | `Optional[str]` | DOI of source paper |
| `confidence` | `float` | Edge confidence in [0, 1] |
| `curation` | `str` | Curation level (`"expert_verified"`, `"extracted"`, `"normalized"`) |

Class method:
- `PSPRelationship.from_legacy(data: dict) -> PSPRelationship` -- Convert from legacy JSON format

### `ChainOfThought`

Complete reasoning chain with source attribution (aria_full mode only).

| Field | Type | Description |
|-------|------|-------------|
| `query_context` | `Dict` | Query metadata |
| `reasoning_steps` | `List[ReasoningStep]` | Ordered reasoning steps |
| `final_reasoning` | `str` | Summary of final reasoning |
| `final_result` | `Dict` | Final prediction |
| `confidence_breakdown` | `Dict[str, float]` | Per-step confidence scores |
| `source_attribution` | `Dict[str, Any]` | Source counts and metadata |
| `tier` | `int` | Reasoning tier used |
| `kg_paths_used` | `int` | Number of KG paths |
| `literature_papers_used` | `int` | Number of literature papers |

### `KnowledgeSource`

Track individual knowledge sources with metadata.

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | `str` | Unique identifier |
| `content` | `str` | Source content |
| `source_type` | `str` | `"kg_node"`, `"kg_edge"`, `"kg_mechanism"`, `"literature"`, `"llm_baseline"` |
| `confidence` | `float` | Source confidence |
| `context` | `str` | Context description |
| `metadata` | `Dict` | Additional metadata |

### `ReasoningStep`

Individual step in chain-of-thought reasoning.

| Field | Type | Description |
|-------|------|-------------|
| `step_id` | `str` | Unique step identifier |
| `description` | `str` | What this step does |
| `evidence_sources` | `List[KnowledgeSource]` | Sources used |
| `reasoning_type` | `str` | `"retrieval"`, `"synthesis"`, `"validation"`, `"inference"`, `"search"` |
| `confidence` | `float` | Step confidence |
| `intermediate_conclusion` | `str` | What this step concluded |

---

## ARIAEngine

The unified entry point for all ARIA operating modes.

### Constructor

```python
engine = ARIAEngine(
    kg=None,                     # Pre-loaded NetworkX DiGraph (or use kg_file)
    kg_file=None,               # Path to KG JSON file
    model="qwen2:7b",           # LLM model name
    mode="aria",                 # Operating mode: baseline, naive_kg, aria, aria_search, aria_full
    similarity_threshold=0.5,   # Min cosine similarity for Tier 2 analogical transfer
    embedding_model="all-MiniLM-L6-v2",  # Sentence-transformer model
    llm_backend="ollama",       # LLM backend type
    llm_base_url="http://localhost:11434",  # LLM API URL
    search_email="research@example.com",    # OpenAlex polite pool email
)
```

**Raises:** `ValueError` if neither `kg` nor `kg_file` is provided in a mode that requires a KG.

### Methods

#### `forward_predict(material, processing, target_property, synthesis_inputs) -> ARIAResult`

Predict material properties from synthesis conditions.

| Parameter | Type | Description |
|-----------|------|-------------|
| `material` | `str` | Host material name (e.g., `"MoS2"`) |
| `processing` | `Dict[str, Any]` | Processing/synthesis parameters |
| `target_property` | `str` | Target property to focus on |
| `synthesis_inputs` | `Dict[str, Any]` | Full synthesis-inputs dict (overrides `material` and `processing`) |

Returns: `ARIAResult`

#### `inverse_design(target_material, target_property, constraints, desired_properties) -> ARIAResult`

Design synthesis conditions to achieve desired properties.

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_material` | `str` | Target material name |
| `target_property` | `str` | Target property description |
| `constraints` | `Dict[str, Any]` | Constraints on the synthesis design |
| `desired_properties` | `Dict[str, Any]` | Full desired-properties dict |

Returns: `ARIAResult`

#### `diagnose_kg() -> Dict[str, Any]`

Return diagnostic statistics about the loaded KG.

---

## Knowledge Graph Module (`aria.kg`)

### `load_kg(path) -> nx.DiGraph`

Load a PSP knowledge graph from an enriched JSON file.

- **path**: Path to JSON file containing a `causal_relationships` array
- **Returns**: NetworkX DiGraph with PSP edge attributes
- **Raises**: `FileNotFoundError`, `ValueError` if no valid relationships found

### `save_kg(graph, path) -> None`

Serialize a PSP knowledge graph to JSON.

### `kg_stats(graph) -> Dict[str, Any]`

Return summary statistics for a PSP knowledge graph.

### `KGDiagnostics`

Comprehensive KG quality analysis.

```python
from aria.kg.diagnostics import KGDiagnostics

diag = KGDiagnostics("path/to/kg.json")  # or KGDiagnostics(graph)
report = diag.generate_report()
diag.print_report(report)
```

Methods:
- `analyze_structure() -> Dict` -- Node/edge counts, density, degree stats, DAG check
- `analyze_content() -> Dict` -- Mechanism coverage, confidence, property counts
- `analyze_coverage(test_queries) -> Dict` -- Query coverage statistics
- `analyze_diversity() -> Dict` -- Semantic diversity using embeddings
- `estimate_kg_gaps() -> Dict` -- How many edges/papers needed for better coverage
- `generate_report() -> Dict` -- Full diagnostic report
- `print_report(report) -> None` -- Print formatted report to stdout
- `save_report(report, output_file) -> None` -- Save report to JSON

### `classify_node_layer(node) -> Optional[str]`

Classify a KG node label into `"Processing"`, `"Structure"`, `"Property"`, or `None`.

### `classify_path_layers(path, graph) -> Dict[str, List[str]]`

Classify each node in a path by PSP layer.

### `psp_layers_covered(path, graph) -> Set[str]`

Return the set of PSP layers that a path covers.

---

## Retrieval Module (`aria.retrieval`)

### `find_psp_paths(graph, start_keywords, end_keywords, max_hops, reverse) -> List[List[str]]`

Find causal pathways in a PSP knowledge graph.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `graph` | `nx.DiGraph` | required | PSP knowledge graph |
| `start_keywords` | `List[str]` | required | Keywords to match source nodes |
| `end_keywords` | `List[str]` | required | Keywords to match target nodes |
| `max_hops` | `int` | `4` | Maximum path length |
| `reverse` | `bool` | `False` | Reverse graph direction (for inverse design) |

### `extract_mechanisms(graph, paths) -> List[Dict[str, str]]`

Extract mechanism text and metadata from edges along paths.

### `NodeMatcher`

Embedding-based similarity search over KG node labels.

```python
from aria.retrieval.similarity import NodeMatcher

matcher = NodeMatcher(graph, model_name="all-MiniLM-L6-v2")
matcher.precompute()
hits = matcher.find_similar("CVD temperature 750C", top_k=5)
best_node, score = matcher.find_most_similar("CVD temperature")
```

### `causal_completeness_score(graph, paths, query) -> float`

Compute C(E, q) = |L(E) intersect L_req(q)| / |L_req(q)|.

### `identify_missing_layers(graph, paths, query) -> Set[PSPLayer]`

Identify which PSP layers are missing from the evidence.

### `rank_paths_by_evidence(paths, graph, weights) -> List[Tuple]`

Rank paths by confidence, evidence richness, and PSP coverage.

### `path_score_details(path, graph) -> Dict[str, float]`

Return the three component scores for a single path.

---

## Reasoning Module (`aria.reasoning`)

### `ReasoningRouter`

Dispatches queries to the appropriate reasoning tier.

```python
from aria.reasoning.router import ReasoningRouter

router = ReasoningRouter(similarity_threshold=0.5)
decision = router.route_forward(query, graph, matcher)
# decision.tier, decision.paths, decision.mechanisms, decision.similar_node
```

### Tier Reasoners

- `Tier1DirectReasoner(llm_client)` -- Exact KG path matching
- `Tier2AnalogicalReasoner(llm_client)` -- Similarity-based transfer learning
- `Tier3FallbackReasoner(llm_client, mode)` -- Pure LLM fallback

### `LiteratureSearcher`

Searches OpenAlex and Semantic Scholar for literature validation.

```python
from aria.reasoning.literature import LiteratureSearcher

searcher = LiteratureSearcher(email="researcher@university.edu")
papers = searcher.search("MoS2 CVD carrier mobility", max_results=10)
```

---

## Evaluation Module (`aria.evaluation`)

### `MetricsComputer`

Compute literature-grounded evaluation metrics.

```python
from aria.evaluation.metrics import MetricsComputer

computer = MetricsComputer(kg=graph)
scores = computer.compute_all(prediction, ground_truth)
# scores: causal_coherence_score, source_grounding_score,
#         internal_validity_score, psp_consistency_score, overall_score
```

Methods:
- `causal_coherence(output, ground_truth) -> Dict[str, float]`
- `source_grounding(output, ground_truth) -> float`
- `internal_validity(output) -> float`
- `psp_consistency(output) -> float`
- `compute_all(output, ground_truth) -> Dict[str, float]`

### `BenchmarkRunner`

Orchestrate benchmark runs across engine modes.

```python
from aria.evaluation.benchmark import BenchmarkRunner

runner = BenchmarkRunner(kg=graph, models=["qwen2:7b"])
results_df = runner.run(task_file="benchmark.jsonl", output_dir="results/")
comparison = BenchmarkRunner.compare(results_df)
```

### `LLMJudge`

LLM-based evaluator with four domain-specific rubrics.

```python
from aria.evaluation.judge import LLMJudge

judge = LLMJudge(backend="ollama", model="qwen2:7b")
result = judge.evaluate_all_metrics(query, prediction, ground_truth)
# result: metric_scores, overall_score (0-100), overall_score_normalized (0-100%)
```

Rubrics (total: 100 points):
- Processing Feasibility (0--40)
- Structure Emergence (0--30)
- Property Consistency (0--20)
- Causal PSP Reasoning (0--10)

---

## Visualization Module (`aria.visualization`)

### `plot_kg(graph, output_path, max_nodes, title, ...)`

Visualize a PSP knowledge graph with JHU color theme.

### `plot_causal_trace(result, output_path)`

Visualize the causal trace of an ARIAResult as a PSP chain diagram.

### `plot_tier_comparison(results, output_path)`

Compare ARIAResult objects across tiers as a grouped bar chart.

---

## Materials Constraints (`aria.materials.constraints`)

### `validate_synthesis_conditions(conditions) -> Dict[str, bool]`

Validate synthesis conditions for physical plausibility.

Returns boolean checks for:
- `temperature_in_range`: Temperature within material limits
- `substrate_temperature_ok`: Substrate can tolerate the temperature
- `atmosphere_dopant_compatible`: Atmosphere works with the dopant
- `precursor_substrate_compatible`: Precursor works on substrate
- `overall_valid`: All checks pass

### `check_thermal_stability(material, temperature) -> bool`

Check whether a material is thermally stable at a given temperature.

### `check_composition_compatibility(precursor, substrate) -> bool`

Check whether a precursor and substrate are compositionally compatible.

### Reference Data

- `MATERIAL_TEMP_RANGES`: Temperature ranges for common 2D materials
- `ATMOSPHERE_DOPANT_COMPAT`: Atmosphere-dopant compatibility matrix
- `PRECURSOR_SUBSTRATE_COMPAT`: Precursor-substrate compatibility matrix