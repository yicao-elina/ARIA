# ARIA Knowledge Graph Pipeline

This document describes how the ARIA 2D Materials PSP (Processing-Structure-Property) Knowledge Graph was built, its schema, and how to extend it.

## Overview

The ARIA KG encodes causal relationships in 2D materials synthesis and doping, structured as directed edges in a Processing-Structure-Property hierarchy. Each relationship represents a causal link such as "Re doping at 0.1 at% *increases* carrier mobility in MoS2" with provenance metadata tracking the evidence source and confidence level.

## Pipeline Stages

### 1. Paper Fetching

Papers were collected from semantic scholar and arXiv APIs using keyword queries targeting 2D material doping and synthesis:

- Keywords: `"2D materials"`, `"transition metal dichalcogenides"`, `"doping"`, `"TMD"`, `"van der Waals"`, `"carrier mobility"`, `"band gap engineering"`
- Target: 76 papers spanning MoS2, WSe2, MoSe2, WTe2, graphene, hBN, black phosphorus, and related heterostructures
- Inclusion: Papers reporting experimental measurements, DFT calculations, or combined computational-experimental studies of doping effects on 2D material properties

### 2. PDF Extraction

PDFs were processed using a multi-stage extraction pipeline:

1. **Text extraction**: PyMuPDF (fitz) for PDF-to-text conversion with section detection
2. **Table extraction**: Camelot for tabular data on synthesis conditions and property measurements
3. **Figure caption extraction**: Regex-based caption parsing for experimental data tables embedded in figures
4. **Cleaning**: LaTeX math normalization, reference removal, and Unicode normalization

### 3. LLM Extraction

Extracted text was fed to an LLM (GPT-4 class) with structured prompts requesting:

- **Causal relationships**: cause_parameter, effect_on_doping, affected_property
- **Mechanism quotes**: Verbatim text supporting the causal claim
- **Confidence levels**: experimentally proven, strongly suggested, hypothesized, etc.
- **Synthesis conditions**: method, temperature, atmosphere, dopant, concentration
- **Quantitative outcomes**: before/after property values, change factors, units

The extraction used few-shot examples and chain-of-thought prompting to improve recall of causal relationships. Each paper yielded 5-15 relationships on average.

### 4. Normalization

Raw extracted relationships were normalized through:

- **Field standardization**: Renaming legacy fields (cause_parameter, effect_on_doping) to PSP format (source, relation, target)
- **Relation inference**: Mapping effect descriptions to canonical relations (increases, decreases, induces, inhibits, affects)
- **PSP type classification**: Using keyword matching to classify each edge as Processing_to_Structure, Structure_to_Property, Processing_to_Property, or Structure_to_Structure
- **Material inference**: Extracting material names from source file names using pattern matching
- **Confidence normalization**: Converting textual confidence levels (experimentally proven, strongly suggested, hypothesized) to numerical values (0.95, 0.85, 0.7)
- **Deduplication**: Removing exact duplicate relationships from the same source paper

## Schema: PSPRelationship

Each relationship in the KG follows the `PSPRelationship` dataclass:

| Field | Type | Description | Example |
|---|---|---|---|
| `source` | str | Cause node (processing condition or structural feature) | `"Re doping (0.1 at%)"` |
| `relation` | str | Causal relation type | `"increases"`, `"decreases"`, `"induces"` |
| `target` | str | Effect node (structural feature or property) | `"drain current by ~10x"` |
| `psp_type` | str | PSP layer classification | `"Processing_to_Property"` |
| `material` | str | Material system | `"MoS2"`, `"WTe2"`, `"graphene"` |
| `evidence_text` | str or None | Supporting evidence sentence from the paper | `"The 0.1 at.% Re-MoS2 BGFET exhibits..."` |
| `paper_doi` | str or None | DOI of source paper | `"10.1103/PhysRevB.102.115411"` |
| `confidence` | float | Edge confidence [0.0, 1.0] | `0.85` |
| `curation` | str | Curation status | `"extracted"`, `"expert_verified"`, `"normalized"` |
| `relationship_id` | str or None | Unique identifier | `"migrated_42"` |

### Legacy fields (preserved for backward compatibility)

| Field | Description |
|---|---|
| `legacy_cause_parameter` | Original cause_parameter from combined_doping_data.json |
| `legacy_effect_on_doping` | Original effect_on_doping field |
| `legacy_confidence_level` | Original textual confidence level |

## PSP Hierarchy

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
|---|---|---|---|---|
| `Processing_to_Structure` | Processing | Structure | How synthesis conditions affect structure | 131 |
| `Structure_to_Property` | Structure | Property | How structural features determine properties | 8 |
| `Processing_to_Property` | Processing | Property | Direct P-to-P shortcuts (skipping structure) | 265 |
| `Structure_to_Structure` | Structure | Structure | Structural analogies between materials | 5 |

### Reasoning Tiers

ARIA uses the PSP hierarchy for its three-tier reasoning cascade:

1. **Tier 1 (DIRECT)**: Exact PSP path match in KG. A complete P->S->P chain is found with evidence.
2. **Tier 2 (ANALOGICAL)**: Similar materials or conditions enable analogical transfer. E.g., predicting Re doping effects in WS2 from MoS2 data.
3. **Tier 3 (FALLBACK)**: No KG evidence available. Falls back to parametric LLM reasoning.

## Statistics

| Metric | Value |
|---|---|
| Total relationships | 409 |
| Unique source papers | 76 |
| Materials covered | 15+ |
| PSP type distribution | P->S: 131, S->P: 8, P->P: 265, S->S: 5 |
| Confidence distribution | 0.95: 311, 0.85: 92, 0.7: 6 |
| Relationships with evidence text | ~30% |
| Relationships with mechanism quotes | ~25% |

## Extending the KG

### Adding new relationships

1. **Prepare data**: Create relationships in the PSPRelationship format (see schema above).
2. **Assign confidence**:
   - `0.95`: Experimentally verified (multiple measurements, reproducible)
   - `0.85`: Supported by strong evidence (DFT + experiment, or clear mechanistic explanation)
   - `0.7`: Hypothesized or weakly supported
3. **Classify PSP type**: Use the `classify_node_layer()` function from `aria.kg.schema` to check that source and target nodes are classified correctly.
4. **Add to KG**: Append to the `causal_relationships` array in `aria_2d_kg_v1.json`.

### Adding a new material

1. Collect papers for the material using the same keyword-based approach.
2. Extract relationships using the LLM extraction pipeline (or manually curate).
3. Set the `material` field to a canonical name (e.g., `"PtSe2"`, `"black_phosphorus"`).
4. Run `python scripts/migrate_kg.py` to regenerate the KG files.

### Upgrading to expert_verified

For relationships extracted by the LLM pipeline, the `curation` field is set to `"extracted"`. To upgrade:

1. Manually verify the causal claim against the original paper.
2. Check that the `evidence_text` accurately quotes the supporting evidence.
3. Confirm that `psp_type` correctly classifies the source-target layers.
4. Change `curation` from `"extracted"` to `"expert_verified"`.

### Running the migration script

```bash
# Default: reads from the 26KDD data directory
python scripts/migrate_kg.py

# Custom source and output
python scripts/migrate_kg.py --source /path/to/combined_doping_data.json --output-dir /path/to/output

# Verbose mode
python scripts/migrate_kg.py -v
```

### Loading the KG in Python

```python
from aria import load_kg

# Load the tiny example KG
kg = load_kg("data/aria_2d_kg_tiny.json")

# Load the full KG
kg = load_kg("data/aria_2d_kg_v1.json")

# Inspect
from aria.kg.graph_store import kg_stats
stats = kg_stats(kg)
print(f"Nodes: {stats['num_nodes']}, Edges: {stats['num_edges']}")
```

## File Locations

| File | Description |
|---|---|
| `data/aria_2d_kg_v1.json` | Full KG with 409 relationships |
| `data/aria_2d_kg_tiny.json` | Curated 6-relationship example KG |
| `data/benchmarks/forward_prediction.jsonl` | Forward prediction benchmark tasks |
| `data/benchmarks/inverse_design.jsonl` | Inverse design benchmark tasks |
| `data/benchmarks/ood_generalization.jsonl` | OOD generalization benchmark tasks |
| `scripts/migrate_kg.py` | KG migration and generation script |
| `scripts/build_kg.py` | KG construction CLI |
| `aria/kg/graph_store.py` | KG load/save/stats module |
| `aria/kg/schema.py` | PSP classification helpers |
| `aria/types.py` | PSPRelationship dataclass definition |