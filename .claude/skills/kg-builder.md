# PSP Knowledge Graph Builder

Build and extend ARIA Processing-Structure-Property knowledge graphs from PDFs or literature search.

## Activation

When the user asks to build, extend, validate, or inspect a PSP knowledge graph, or mentions "kg-builder", "knowledge graph construction", "extract relationships", "add edges to KG", or "validate KG".

## Modes

### PDF Mode -- Extract relationships from PDF documents

1. Accept a PDF file path (or multiple) from the user.
2. Read the PDF text content using an available PDF reader.
3. Prompt the LLM to extract causal relationships in PSP format. For each relationship, request:
   - `source` (cause parameter, e.g. "growth_temperature:750C")
   - `relation` (e.g. "increases", "decreases", "induces")
   - `target` (effect, e.g. "crystallinity")
   - `psp_type` (one of: `Processing_to_Structure`, `Structure_to_Property`, `Processing_to_Property`, `Structure_to_Structure`, `Processing_to_Processing`)
   - `material` (e.g. "MoS2")
   - `evidence_text` (verbatim supporting sentence from the PDF)
   - `paper_doi` (if available)
   - `confidence` (0.0--1.0)
4. Normalize each extracted relationship into a `PSPRelationship` dataclass:
   ```python
   from aria.types import PSPRelationship
   rel = PSPRelationship(
       source=...,
       relation=...,
       target=...,
       psp_type=...,
       material=...,
       evidence_text=...,
       paper_doi=...,
       confidence=...,
       curation="extracted",
   )
   ```
5. Add each relationship to an existing KG or create a new one.

### Keyword Mode -- Search literature and extract relationships

1. Accept search queries from the user (e.g. "MoS2 CVD doping mobility").
2. Initialize the literature searcher:
   ```python
   from aria.reasoning.literature import LiteratureSearcher
   searcher = LiteratureSearcher(email=os.environ.get("ARIA_SEARCH_EMAIL", "research@example.com"))
   ```
   Use the user's email for the OpenAlex polite pool when available (set via `ARIA_SEARCH_EMAIL` in `.env`).
3. Search for papers:
   ```python
   results = searcher.search(query="MoS2 CVD carrier mobility", max_results=10, use_both=True)
   # Or individually:
   openalex_results = searcher.search_openalex(query="MoS2 CVD carrier mobility", max_results=5)
   s2_results = searcher.search_semantic_scholar(query="MoS2 CVD carrier mobility", max_results=5)
   ```
   Each result is a dict with keys: `title`, `abstract`, `url`, `year`, `citations`, `authors`, `source`.
4. From each result's abstract, prompt the LLM to extract PSP relationships (same schema as PDF mode).
5. Normalize into `PSPRelationship` instances.

### Legacy Format Conversion

If the input data uses the legacy combined format with fields like `cause_parameter`, `effect_on_doping`, `affected_property`, `mechanism_quote`, `confidence_level`, and `source_file`, convert using:

```python
from aria.types import PSPRelationship
rel = PSPRelationship.from_legacy(legacy_dict)
```

This automatically maps `cause_parameter` to `source`, infers `relation` from `effect_on_doping`, and assigns `psp_type`.

## KG Format Requirements

The JSON file format consumed by `load_kg()` **must** include the `cause_parameter` and `effect_on_doping` fields in each relationship entry. These are required fields in the canonical enriched JSON format:

```json
{
  "causal_relationships": [
    {
      "cause_parameter": "growth_temperature:750C",
      "effect_on_doping": "increases crystallinity",
      "affected_property": "crystallinity",
      "mechanism_quote": "Higher growth temperature promotes larger grain sizes...",
      "confidence_level": "high",
      "source_file": "mos2_cvd_study.pdf",
      "paper_doi": "10.1234/example",
      "relationship_id": "R001"
    }
  ]
}
```

If you are creating new relationships from scratch (not converting legacy data), still populate `cause_parameter` and `effect_on_doping` to ensure `load_kg()` compatibility. The `PSPRelationship.from_legacy()` method consumes this format.

## Loading and Saving

```python
from aria.kg.graph_store import load_kg, save_kg, kg_stats

# Load existing KG
graph = load_kg("data/aria_2d_kg_v1.json")

# Check statistics
stats = kg_stats(graph)
print(stats)  # e.g., {"nodes": 777, "edges": 421, "psp_types": {...}}

# Save after modifications
save_kg(graph, "data/aria_2d_kg_v2.json")
```

When building a new KG from scratch, construct a JSON file with the `causal_relationships` array (see format above) and load it with `load_kg()`.

## Validation

After building or extending a KG, always validate:

```python
from aria.kg.diagnostics import KGDiagnostics
diag = KGDiagnostics(graph)  # accepts a DiGraph or a file path
report = diag.generate_report()
```

The report covers: structural quality, content richness, query coverage, semantic diversity, and data-gap estimates. Review warnings and fix issues before saving.

## Workflow Summary

1. Choose mode (PDF or keyword).
2. Extract raw relationships (LLM-assisted).
3. Normalize to `PSPRelationship` (direct construction or `from_legacy()`).
4. Load existing KG or create new JSON with `causal_relationships` array.
5. Add relationships as edges in the `DiGraph`.
6. Validate with `KGDiagnostics.generate_report()`.
7. Save with `save_kg(graph, path)`.
8. Report statistics with `kg_stats(graph)`.