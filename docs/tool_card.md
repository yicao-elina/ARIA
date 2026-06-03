# ARIA Tool Card

**Intended use, failure modes, and safety information for the ARIA reasoning system.**

---

## 1. Tool Description

**Name:** ARIA (Causal-Aware Reasoning for Materials Discovery)

**Version:** 0.1.0

**Category:** AI-assisted materials reasoning tool

**Description:** ARIA is a causal evidence-gating framework that helps LLMs reason over Processing-Structure-Property (PSP) pathways for materials synthesis and property prediction. Unlike standard RAG, ARIA activates retrieved evidence only when it forms a causally complete PSP path.

**Core capability:** Given a query about materials synthesis or properties, ARIA:
1. Searches a PSP knowledge graph for relevant causal pathways
2. Evaluates whether the retrieved evidence is causally complete
3. Routes through a 3-tier cascade (Direct, Analogical, Fallback) based on evidence quality
4. Returns predictions with confidence scores, causal traces, and missing evidence flags

---

## 2. Intended Users

| User Type | Intended Use |
|-----------|-------------|
| Materials scientists | Exploring synthesis conditions, understanding PSP relationships, guiding experimental design |
| Computational materials researchers | Benchmarking reasoning systems, studying causal completeness effects |
| AI researchers | Evaluating retrieval-augmented generation, studying evidence gating mechanisms |
| Students | Learning about PSP causal hierarchies in 2D materials |

**Prerequisites:**
- Familiarity with materials science concepts (synthesis methods, crystal structure, electronic properties)
- Understanding of causal reasoning basics
- Python 3.9+ with required dependencies

---

## 3. Use Cases

### Supported

- **Forward prediction:** Given synthesis conditions, predict resulting material properties
- **Inverse design:** Given target properties, suggest synthesis conditions
- **Knowledge graph exploration:** Inspect and analyze PSP relationships in 2D materials
- **Quality assessment:** Diagnose KG completeness, identify gaps, estimate coverage
- **Benchmarking:** Compare ARIA modes (baseline, naive_kg, aria) on standardized tasks

### Not Supported

- Automated experimental execution (ARIA provides suggestions, not recipes)
- Multi-step synthesis planning beyond the KG's scope
- Real-time process control
- Safety assessment or hazard analysis

---

## 4. Operating Modes

| Mode | KG Used? | Literature? | CoT? | Description |
|------|----------|-------------|------|-------------|
| `baseline` | No | No | No | Pure LLM parametric knowledge |
| `naive_kg` | Yes | No | No | KG evidence concatenated without causal gating |
| `aria` | Yes | No | No | 3-tier causal cascade with evidence gating |
| `aria_search` | Yes | Yes | No | 3-tier + literature search (OpenAlex, Semantic Scholar) |
| `aria_full` | Yes | Yes | Yes | 3-tier + literature + full chain-of-thought transparency |

**Recommendation:** Use `aria` mode for most applications. Use `baseline` and `naive_kg` for ablation studies. Use `aria_search` when literature validation is needed. Use `aria_full` for maximum transparency.

---

## 5. Confidence Interpretation

ARIA reports confidence scores in [0, 1]. Interpretation guidelines:

| Confidence Range | Tier | Interpretation |
|------------------|------|----------------|
| 0.8 -- 1.0 | Tier 1 (Direct) | Strong causal evidence found in KG. PSP chain is complete. High reliability. |
| 0.5 -- 0.8 | Tier 2 (Analogical) | Similar material found in KG. Prediction is adapted from analogous case. Moderate reliability. |
| 0.0 -- 0.5 | Tier 3 (Fallback) | No KG evidence. Prediction relies on LLM parametric knowledge. Low reliability. |

**Important:** Confidence scores are not calibrated probabilities. They reflect the quality of the causal evidence, not the probability that the prediction is exactly correct.

**Missing evidence:** The `missing_evidence` field in `ARIAResult` lists PSP layers not covered by the evidence. A prediction with `missing_evidence=["Structure"]` means the causal chain jumps directly from Processing to Property without structural explanation.

---

## 6. Failure Modes

### Known Limitations

1. **KG coverage gaps:** The knowledge graph does not cover all materials, synthesis methods, or properties. Queries about materials not in the KG will fall to Tier 3 (pure LLM).

2. **Incomplete PSP chains:** Even when KG evidence is found, it may not form a complete Processing -> Structure -> Property chain. ARIA reports this via `missing_evidence`.

3. **LLM hallucination:** Tier 3 predictions rely entirely on the LLM's parametric knowledge and may contain inaccuracies or fabricated values.

4. **Analogical transfer errors:** Tier 2 predictions adapt knowledge from similar materials, which may not transfer correctly to the target case.

5. **Stale literature:** `aria_search` and `aria_full` modes query OpenAlex and Semantic Scholar, which may return outdated or retracted papers.

6. **Temperature and pressure ranges:** The constraint validation module uses approximate ranges that may not reflect the latest experimental findings.

7. **Single-step predictions:** ARIA predicts properties for a single set of synthesis conditions. It does not optimize over a design space.

### How to Detect Failures

- Check `result.tier`: Tier 3 (FALLBACK) indicates no KG evidence
- Check `result.confidence`: Values below 0.5 indicate low-reliability predictions
- Check `result.missing_evidence`: Non-empty lists indicate incomplete causal chains
- Check `result.kg_paths_used`: Zero paths means no KG evidence was found
- Run `KGDiagnostics` to assess KG coverage for your queries

### Mitigation Strategies

- Use `aria_search` or `aria_full` mode for additional literature validation
- Enrich the knowledge graph for your specific materials domain
- Cross-validate predictions with experimental data
- Use physical feasibility checks (`aria.materials.constraints`) to flag unrealistic conditions

---

## 7. Safety Warnings

**CRITICAL:** ARIA is a research tool, not a substitute for experimental validation.

1. **Do not directly implement** predicted synthesis conditions without expert review and safety assessment. High-temperature, high-pressure, and reactive atmosphere processes carry significant safety risks.

2. **Confidence scores are NOT guarantees of correctness.** A high confidence Tier 1 prediction may still be wrong if the underlying KG data is incorrect or outdated.

3. **The constraint validation module provides approximate checks only.** It does not replace proper thermodynamic calculations, phase diagram analysis, or expert safety review.

4. **Temperature and pressure ranges** in `MATERIAL_TEMP_RANGES` are representative ranges from the literature, not definitive stability limits.

5. **Atmosphere-dopant compatibility** in `ATMOSPHERE_DOPANT_COMPAT` is a simplification. Real compatibility depends on exact concentrations, temperatures, and substrates.

6. **Precursor-substrate compatibility** in `PRECURSOR_SUBSTRATE_COMPAT` covers only the most common combinations. Unknown combinations default to compatible.

7. **Always verify** ARIA predictions against:
   - Published experimental data
   - Phase diagrams and thermodynamic databases
   - Safety data sheets (SDS) for all chemicals
   - Equipment manufacturer specifications

---

## 8. Reporting Issues

If you encounter:
- **Incorrect predictions** (ARIA gives a confident but wrong answer)
- **Missing KG coverage** (common materials or properties not represented)
- **Safety concerns** (ARIA suggests dangerous or impossible conditions)
- **Software bugs** (crashes, incorrect output, unexpected behavior)

Please open an issue on the GitHub repository with:
- The query you used
- The ARIAResult you received
- The expected behavior
- Any relevant safety implications

---

## 9. Citation

If you use ARIA in your research, please cite:

```bibtex
@software{aria2024,
  title = {ARIA: Causal-Aware Reasoning for Materials Discovery},
  author = {ARIA Team},
  year = {2024},
  version = {0.1.0},
  url = {https://github.com/aria-materials/aria}
}
```

---

## 10. Contact

For questions, concerns, or collaboration inquiries, please contact the ARIA Team through the GitHub repository.