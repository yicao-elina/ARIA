# ARIA-2D-KG Knowledge Graph Card

**Construction, schema, limitations, and extending the ARIA PSP Knowledge Graph.**

---

## 1. Overview

ARIA-2D-KG is a directed knowledge graph encoding causal Processing-Structure-Property (PSP) relationships for 2D materials synthesis and property prediction. Each edge represents a causal link (e.g., "CVD temperature 750C increases crystallinity") with provenance metadata for evidence tracking.

| Property | Value |
|----------|-------|
| Version | 1.0.0 |
| Format | JSON (`causal_relationships` array) |
| Full KG | `data/aria_2d_kg_v1.json` (421 relationships, 777+ nodes) |
| Tiny KG | `data/aria_2d_kg_tiny.json` (6 relationships, for demos) |
| License | MIT |
| Loading API | `from aria import load_kg` |

---

## 2. Construction

### 2.1 Paper Fetching

Papers were collected from Semantic Scholar and arXiv APIs using keyword queries targeting 2D material doping and synthesis:

- Keywords: `"2D materials"`, `"transition metal dichalcogenides"`, `"doping"`, `"TMD"`, `"van der Waals"`, `"carrier mobility"`, `"band gap engineering"`
- Target: 76 papers spanning MoS2, WSe2, MoSe2, WTe2, graphene, hBN, black phosphorus, and related heterostructures
- Inclusion criteria: Papers reporting experimental measurements, DFT calculations, or combined computational-experimental studies of doping effects on 2D material properties

### 2.2 PDF Extraction

PDFs were processed through a multi-stage extraction pipeline:

1. **Text extraction**: PyMuPDF (fitz) for PDF-to-text conversion with section detection
2. **Table extraction**: Camelot for tabular data on synthesis conditions and property measurements
3. **Figure caption extraction**: Regex-based caption parsing for experimental data tables embedded in figures
4. **Cleaning**: LaTeX math normalization, reference removal, and Unicode normalization

### 2.3 LLM Extraction

Extracted text was fed to an LLM (GPT-4 class) with structured prompts requesting:

- **Causal relationships**: cause_parameter, effect_on_doping, affected_property
- **Mechanism quotes**: Verbatim text supporting the causal claim
- **Confidence levels**: experimentally proven, strongly suggested, hypothesized, etc.
- **Synthesis conditions**: method, temperature, atmosphere, dopant, concentration
- **Quantitative outcomes**: before/after property values, change factors, units

The extraction used few-shot examples and chain-of-thought prompting to improve recall of causal relationships. Each paper yielded 5-15 relationships on average.

### 2.4 Normalization

Raw extracted relationships were normalized through:

1. **Field standardization**: Renaming legacy fields (cause_parameter, effect_on_doping) to PSP format (source, relation, target) via `PSPRelationship.from_legacy()`
2. **Relation inference**: Mapping effect descriptions to canonical relations (increases, decreases, induces, inhibits, affects) via `_infer_relation()`
3. **PSP type classification**: Keyword-based classification of each edge as Processing_to_Structure, Structure_to_Property, Processing_to_Property, or Structure_to_Structure via `_infer_psp_type()`
4. **Material inference**: Extracting material names from source file names via `_infer_material()` and extended pattern matching
5. **Confidence normalization**: Converting textual confidence levels (experimentally proven, strongly suggested, hypothesized) to numerical values (0.95, 0.85, 0.7) via `_parse_confidence()`
6. **Deduplication**: Removing exact duplicate relationships from the same source paper

The normalization pipeline is implemented in `scripts/migrate_kg.py` and `scripts/build_kg.py`.

---

## 3. Schema

### PSPRelationship Fields

Each edge in the KG follows the `PSPRelationship` dataclass (defined in `aria/types.py`):

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `source` | `str` | Cause node (processing condition or structural feature) | `"Re doping (0.1 at%)"` |
| `relation` | `str` | Causal relation type | `"increases"`, `"decreases"`, `"induces"` |
| `target` | `str` | Effect node (structural feature or property) | `"drain current by ~10x"` |
| `psp_type` | `str` | PSP layer classification | `"Processing_to_Property"` |
| `material` | `str` | Material system | `"MoS2"`, `"WTe2"`, `"graphene"` |
| `evidence_text` | `Optional[str]` | Supporting evidence sentence from the paper | `"The 0.1 at.% Re-MoS2 BGFET exhibits..."` |
| `paper_doi` | `Optional[str]` | DOI of source paper | `"10.1103/PhysRevB.102.115411"` |
| `confidence` | `float` | Edge confidence in [0.0, 1.0] | `0.85` |
| `curation` | `str` | Curation level | `"expert_verified"`, `"extracted"`, `"normalized"` |
| `relationship_id` | `Optional[str]` | Unique identifier | `"migrated_42"` |

### Legacy Fields (Preserved for Backward Compatibility)

| Field | Description |
|-------|-------------|
| `legacy_cause_parameter` | Original cause_parameter from combined_doping_data.json |
| `legacy_effect_on_doping` | Original effect_on_doping field |
| `legacy_confidence_level` | Original textual confidence level |

### JSON Format

The canonical format uses a top-level `causal_relationships` array:

```json
{
  "version": "1.0.0",
  "description": "ARIA 2D Materials PSP Knowledge Graph",
  "schema": "PSPRelationship",
  "total_relationships": 421,
  "causal_relationships": [
    {
      "source": "CVD temperature 750C",
      "relation": "increases",
      "target": "crystallinity",
      "psp_type": "Processing_to_Structure",
      "material": "MoS2",
      "evidence_text": "Higher temperature leads to larger grain sizes...",
      "paper_doi": "10.1038/...",
      "confidence": 0.87,
      "curation": "expert_verified",
      "relationship_id": "migrated_1"
    }
  ]
}
```

---

## 4. PSP Hierarchy

The PSP (Processing-Structure-Property) hierarchy organizes causal relationships into three layers:

```
Processing (P)          Structure (S)          Property (P)
    |                       |                       |
    |  temperature          |  crystallinity        |  mobility
    |  pressure             |  phase                |  band gap
    |  atmosphere           |  defect density       |  conductivity
    |  dopant               |  doping level          |  carrier type
    |  method               |  lattice distortion    |  Seebeck coeff.
    |  concentration        |  vacancy formation     |  HER activity
    v                       v                       v
```

### Edge Types

| PSP Type | Source Layer | Target Layer | Description | Count |
|----------|-------------|-------------|-------------|-------|
| `Processing_to_Structure` | Processing | Structure | How synthesis conditions affect structure | 131 |
| `Structure_to_Property` | Structure | Property | How structural features determine properties | 8 |
| `Processing_to_Property` | Processing | Property | Direct shortcut (skips Structure) | 265 |
| `Structure_to_Structure` | Structure | Structure | Structural analogies between materials | 5 |

### Reasoning Tiers

ARIA uses the PSP hierarchy for its three-tier reasoning cascade:

1. **Tier 1 (DIRECT)**: Exact PSP path match in KG. A complete P -> S -> P chain is found with evidence.
2. **Tier 2 (ANALOGICAL)**: Similar materials or conditions enable analogical transfer. E.g., predicting Re doping effects in WS2 from MoS2 data.
3. **Tier 3 (FALLBACK)**: No KG evidence available. Falls back to parametric LLM reasoning.

### Causal Completeness

A retrieved evidence set E is PSP-complete for a query q if it covers at least one directed path connecting the intervention variable and outcome variable through the required PSP layers:

```
C(E, q) = |L(E) intersect L_req(q)| / |L_req(q)|
```

where L = {Processing, Structure, Property}. When C(E, q) < 1.0, some required layers are missing, and ARIA reports this via `missing_evidence`.

---

## 5. Statistics

| Metric | Value |
|--------|-------|
| Total relationships | 421 |
| Unique source papers | 76 |
| Materials covered | 15+ |
| Processing_to_Structure edges | 131 |
| Structure_to_Property edges | 8 |
| Processing_to_Property edges | 265 |
| Structure_to_Structure edges | 5 |
| Confidence = 0.95 (experimentally proven) | 311 |
| Confidence = 0.85 (strongly suggested) | 92 |
| Confidence = 0.7 (hypothesized) | 6 |
| Relationships with evidence text | ~30% |
| Relationships with mechanism quotes | ~25% |

### Tiny Demo KG

The `aria_2d_kg_tiny.json` contains 6 curated relationships covering:

| Metric | Value |
|--------|-------|
| Nodes | 7 |
| Edges | 7 |
| Processing -> Structure | 4 |
| Structure -> Structure | 1 |
| Structure -> Property | 2 |
| Is DAG | Yes |

---

## 6. Limitations

### 6.1 Coverage Gaps

- **Structure-to-Property edges** are underrepresented (only 8 out of 421 edges). Most relationships skip directly from Processing to Property without structural explanation.
- **Materials coverage** is biased toward MoS2 and graphene. Less-studied materials (hBN, black phosphorus, PtSe2) have fewer relationships.
- **Quantitative data** is sparse. Most relationships encode qualitative causal links rather than numerical predictions.

### 6.2 Quality Issues

- **~70% of relationships lack evidence text.** The mechanism quotes field is populated for only ~25% of edges.
- **Confidence scores are coarse.** The three-tier system (0.95, 0.85, 0.7) does not capture fine-grained uncertainty.
- **Curation status.** Most relationships are labeled `"extracted"` (from LLM pipeline). Only a subset have been `"expert_verified"`.

### 6.3 Bias

- **Publication bias:** The KG reflects what is published, not what is true. Positive results (doping improves properties) are overrepresented.
- **Material bias:** MoS2 and graphene dominate the KG, reflecting their prevalence in the literature.
- **Method bias:** CVD and MBE synthesis methods are well-represented; sputtering and solution-based methods less so.

### 6.4 Structural Limitations

- **No temporal ordering:** Edges do not encode the sequence of processing steps.
- **No conditional relationships:** Edges do not capture "if-then" conditional logic (e.g., "increases mobility *only if* temperature is below 800C").
- **No uncertainty ranges:** Confidence is a single scalar, not a distribution.
- **No negative results:** The KG encodes what *does* happen, not what *doesn't*.

---

## 7. Extending the KG

### 7.1 Adding New Relationships

1. Prepare data in PSPRelationship format (see schema above).
2. Assign confidence:
   - `0.95`: Experimentally verified (multiple measurements, reproducible)
   - `0.85`: Supported by strong evidence (DFT + experiment, or clear mechanistic explanation)
   - `0.7`: Hypothesized or weakly supported
3. Classify PSP type: Use `classify_node_layer()` from `aria.kg.schema` to verify that source and target nodes are classified correctly.
4. Append to the `causal_relationships` array in `aria_2d_kg_v1.json`.

Example:

```python
from aria.types import PSPRelationship

new_rel = PSPRelationship(
    source="CVD temperature 850C",
    relation="increases",
    target="grain size",
    psp_type="Processing_to_Structure",
    material="WS2",
    evidence_text="Higher CVD temperature increases WS2 grain size...",
    paper_doi="10.1234/ws2-cvd",
    confidence=0.85,
    curation="expert_verified",
    relationship_id="manual_001",
)
```

### 7.2 Adding a New Material

1. Collect papers for the material using the same keyword-based approach.
2. Extract relationships using the LLM extraction pipeline (or manually curate).
3. Set the `material` field to a canonical name (e.g., `"PtSe2"`, `"black_phosphorus"`).
4. Run `python scripts/migrate_kg.py` or `python scripts/build_kg.py merge` to regenerate the KG files.

### 7.3 Upgrading to Expert Verified

For relationships extracted by the LLM pipeline, the `curation` field is set to `"extracted"`. To upgrade:

1. Manually verify the causal claim against the original paper.
2. Check that `evidence_text` accurately quotes the supporting evidence.
3. Confirm that `psp_type` correctly classifies the source-target layers.
4. Change `curation` from `"extracted"` to `"expert_verified"`.

### 7.4 Programmatic Access

```python
from aria import load_kg, save_kg
from aria.kg.graph_store import kg_stats
from aria.kg.diagnostics import KGDiagnostics

# Load and inspect
kg = load_kg("data/aria_2d_kg_v1.json")
stats = kg_stats(kg)

# Diagnose quality
diag = KGDiagnostics("data/aria_2d_kg_v1.json")
report = diag.generate_report()
diag.print_report(report)

# Add edges programmatically
kg.add_edge("new source", "new target",
            mechanism="New mechanism quote",
            psp_type="Processing_to_Structure",
            relation="increases",
            confidence=0.85)

# Save
save_kg(kg, "data/aria_2d_kg_v1_updated.json")
```

### 7.5 Validation

Use the build_kg CLI to validate the KG after modifications:

```bash
# Validate structure
python scripts/build_kg.py validate data/aria_2d_kg_v1.json

# Print statistics
python scripts/build_kg.py stats data/aria_2d_kg_v1.json

# Run full diagnostics
python scripts/build_kg.py diagnose data/aria_2d_kg_v1.json

# Merge with new relationships
python scripts/build_kg.py merge data/aria_2d_kg_v1.json data/new_rels.json -o data/aria_2d_kg_v2.json
```

---

## 8. File Locations

| File | Description |
|------|-------------|
| `data/aria_2d_kg_v1.json` | Full KG with 421 relationships |
| `data/aria_2d_kg_tiny.json` | Curated 6-relationship example KG |
| `data/benchmarks/forward_prediction.jsonl` | Forward prediction benchmark tasks |
| `data/benchmarks/inverse_design.jsonl` | Inverse design benchmark tasks |
| `data/benchmarks/ood_generalization.jsonl` | OOD generalization benchmark tasks |
| `scripts/migrate_kg.py` | KG migration and generation script |
| `scripts/build_kg.py` | KG construction CLI |
| `aria/kg/graph_store.py` | KG load/save/stats module |
| `aria/kg/schema.py` | PSP classification helpers |
| `aria/kg/diagnostics.py` | KG quality diagnostics |
| `aria/types.py` | PSPRelationship dataclass definition |