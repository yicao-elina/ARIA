# ARIA-2D-KG Data Card

**Following the Datasheets for Datasets format (Gebru et al., 2021)**

---

## 1. Motivation

**Purpose:** The ARIA-2D-KG knowledge graph was created to support causal-aware reasoning for 2D materials synthesis and property prediction. It encodes Processing-Structure-Property (PSP) causal relationships extracted from the materials science literature, enabling ARIA's 3-tier reasoning cascade.

**Creators:** ARIA Team at Johns Hopkins University.

**Funding:** This work was supported by research grants for AI-driven materials discovery.

---

## 2. Composition

**Instance types:** Each instance is a causal relationship (directed edge) in a knowledge graph.

**Node types:**
- Processing nodes: Synthesis conditions (temperature, pressure, atmosphere, method, doping, substrate, etc.)
- Structure nodes: Material structural features (crystallinity, defect density, grain size, phase, doping level, etc.)
- Property nodes: Measurable properties (carrier mobility, conductivity, band gap, transconductance, etc.)

**Edge types (PSPRelationship):**

| PSP Type | Description | Example |
|----------|-------------|---------|
| Processing_to_Structure | Synthesis condition causes structural change | CVD temperature 750C -> improved crystallinity |
| Structure_to_Property | Structural feature determines property | improved crystallinity -> higher carrier mobility |
| Processing_to_Property | Direct shortcut (skips Structure) | doping Nb -> increased conductivity |
| Structure_to_Structure | Structural feature influences another | grain growth -> improved crystallinity |
| Processing_to_Processing | Process parameter influences another | annealing time -> temperature profile |

**Edge attributes:**
- `source`: Cause node label (string)
- `target`: Effect node label (string)
- `relation`: Causal relation type (`"increases"`, `"decreases"`, `"induces"`, `"inhibits"`, `"affects"`)
- `mechanism`: Textual explanation of the causal mechanism
- `confidence`: Confidence score in [0, 1]
- `psp_type`: PSP layer classification
- `source_file`: Origin data file
- `source_doi`: DOI of the source paper
- `affected_property`: The property affected by this edge
- `relationship_id`: Unique identifier

**Dataset size:** The tiny demo KG contains 7 nodes and 7 edges. The full ARIA-2D-KG-v1 contains hundreds of nodes and edges covering MoS2, WS2, WSe2, MoSe2, MoTe2, WTe2, graphene, hBN, and black phosphorus.

**Missing data:** Not all PSP chains are complete. Some edges lack mechanism quotes or confidence scores. The `KGDiagnostics` class provides detailed gap analysis.

---

## 3. Collection Process

**Data acquisition:** Relationships were extracted from the peer-reviewed materials science literature using a combination of:
1. Manual curation by domain experts
2. Semi-automated extraction from papers with known DOIs
3. Normalization and deduplication across sources

**Sampling strategy:** The dataset covers the most commonly studied 2D materials (TMDs, graphene, hBN, black phosphorus) with focus on CVD, MOCVD, and sputtering synthesis methods.

**Data validation:** Each relationship was reviewed for:
- Correct PSP layer classification
- Accurate causal direction (cause -> effect)
- Mechanism text quality
- Appropriate confidence scoring

---

## 4. Preprocessing / Cleaning

**Normalization steps:**
1. Node labels normalized to lowercase with underscores
2. PSP type inferred from keyword matching (`_infer_psp_type`)
3. Relation type inferred from effect text (`_infer_relation`)
4. Confidence parsed from textual descriptions (`_parse_confidence`)
5. Material name inferred from source file (`_infer_material`)
6. Edges with "unknown" or "n/a" values were silently skipped

**Format:** The canonical format is JSON with a top-level `causal_relationships` array. Each element has fields: `cause_parameter`, `effect_on_doping`, `affected_property`, `mechanism_quote`, `confidence_level`, `source_file`, `source_doi`, and `relationship_id`.

**Loading:** Use `aria.load_kg(path)` to load into a NetworkX DiGraph. The loader applies `PSPRelationship.from_legacy()` to convert from the legacy format.

---

## 5. Uses

**Intended uses:**
- Causal-aware reasoning for materials property prediction (forward prediction)
- Inverse synthesis design (given target properties, find synthesis conditions)
- Knowledge graph quality assessment and gap analysis
- Benchmarking retrieval-augmented reasoning systems
- Evaluating the impact of causal completeness on reasoning quality

**Unintended uses:**
- The KG should not be used as a substitute for experimental validation
- Predictions from ARIA are not guaranteed to be physically realizable
- The KG does not encode safety constraints or equipment limitations

---

## 6. Distribution

**License:** MIT License

**Access:** The demo KG (`aria_2d_kg_tiny.json`) is included in the package. The full ARIA-2D-KG-v1 dataset will be released upon publication.

**Format:** JSON file with `causal_relationships` array.

---

## 7. Maintenance

**Updates:** The dataset will be updated as new relationships are extracted from the literature. Version numbers follow semantic versioning.

**Reporting issues:** Please open an issue on the GitHub repository for data quality concerns, missing relationships, or classification errors.

**Version:** 0.1.0

---

## 8. Ethical Considerations

**Potential harms:**
- Predicted synthesis conditions should not be attempted without proper safety review and experimental validation
- The KG represents current scientific knowledge, which may contain errors or outdated information
- Confidence scores reflect literature consensus, not experimental certainty

**Mitigations:**
- `aria.materials.constraints` provides physical feasibility checks for temperature, atmosphere, and substrate compatibility
- ARIA always reports confidence scores and missing evidence
- Users are warned when predictions fall to Tier 3 (no KG evidence)

---

## 9. Key Statistics (Demo KG)

| Metric | Value |
|--------|-------|
| Nodes | 7 |
| Edges | 7 |
| Root nodes (Processing) | 2 |
| Leaf nodes (Property) | 1 |
| Intermediate (Structure) | 4 |
| Processing_to_Structure edges | 4 |
| Structure_to_Structure edges | 1 |
| Structure_to_Property edges | 2 |
| Average confidence | 0.85 |
| Mechanism coverage | 100% |
| Is DAG | Yes |