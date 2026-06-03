"""
ARIA Evaluation Metrics -- Literature-Grounded Assessment.

Computes causal coherence, source grounding, internal validity, and
PSP consistency metrics for ARIAResult predictions.  Ported from
``metrics_v2_improved.py`` and refactored into a MetricsComputer class
with clean method signatures.

Literature grounding:
  - Pearl (2019): Intervention testing / do-calculus
  - Schölkopf et al. (2021): Mechanistic modularity
  - Geiger et al. (2023): Causal abstraction
  - Thorne et al. (2018): FEVER evidence verification
  - Wiegreffe & Marasović (2021): Faithfulness testing
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded NLP / embedding models
# ---------------------------------------------------------------------------
_nlp = None
_embedding_model = None


def _get_nlp():
    """Return a SpaCy English model, downloading if necessary."""
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    except OSError:
        import spacy
        import os
        os.system("python -m spacy download en_core_web_sm > /dev/null 2>&1")
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _get_embedding_model():
    """Return a sentence-transformers model (all-MiniLM-L6-v2 by default)."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    from sentence_transformers import SentenceTransformer
    _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def extract_causal_edges(
    chain_of_thought: List[str],
    embedding_model=None,
) -> List[Tuple[str, str, str]]:
    """Extract causal relationships from a chain-of-thought using NLP.

    Parameters
    ----------
    chain_of_thought:
        List of reasoning step strings.
    embedding_model:
        Optional sentence-transformers model (unused for extraction,
        kept for API compatibility with the original code).

    Returns
    -------
    list of (source, target, mechanism) tuples
        Each tuple represents a causal claim extracted from the text.
    """
    nlp = _get_nlp()
    edges: List[Tuple[str, str, str]] = []

    for step in chain_of_thought:
        if not isinstance(step, str):
            continue
        doc = nlp(step)
        for token in doc:
            if token.lemma_ in [
                "cause", "lead", "result", "enable", "produce", "induce",
            ]:
                subject = [
                    child.text
                    for child in token.head.children
                    if child.dep_ == "nsubj"
                ]
                obj = [
                    child.text
                    for child in token.children
                    if child.dep_ in ("dobj", "attr")
                ]
                if subject and obj:
                    edges.append((subject[0], obj[0], token.lemma_))

    return edges


def verify_causal_edge_in_kg(
    kg: nx.DiGraph,
    source: str,
    target: str,
    mechanism: str,
) -> bool:
    """Check whether a causal edge (source -> target) exists in the KG.

    Uses fuzzy substring matching on node labels so that minor naming
    differences do not cause false negatives.
    """
    source_nodes = [n for n in kg.nodes() if source.lower() in str(n).lower()]
    target_nodes = [n for n in kg.nodes() if target.lower() in str(n).lower()]
    if not source_nodes or not target_nodes:
        return False
    for s in source_nodes:
        for t in target_nodes:
            if nx.has_path(kg, s, t):
                return True
    return False


def extract_atomic_claims(text: str) -> List[str]:
    """Break a mechanism explanation into atomic verifiable claims.

    Uses SpaCy sentence segmentation and splits on causal connectives.
    """
    nlp = _get_nlp()
    doc = nlp(text)
    claims: List[str] = []
    for sent in doc.sents:
        subclaims = re.split(r",\s*(?:which|that|and)\s+", sent.text)
        claims.extend(c.strip() for c in subclaims if len(c.strip()) > 10)
    return claims


def verify_claim_in_kg(
    kg: nx.DiGraph,
    claim: str,
    embedding_model=None,
) -> bool:
    """Verify whether *claim* is supported by paths in the knowledge graph.

    Extracts named entities from *claim* and checks for KG paths between
    any pair of entities.
    """
    nlp = _get_nlp()
    doc = nlp(claim)
    entities = [ent.text for ent in doc.ents]
    if len(entities) < 2:
        return False

    for i, e1 in enumerate(entities[:-1]):
        for e2 in entities[i + 1 :]:
            n1 = [n for n in kg.nodes() if e1.lower() in str(n).lower()]
            n2 = [n for n in kg.nodes() if e2.lower() in str(n).lower()]
            for a in n1:
                for b in n2:
                    if nx.has_path(kg, a, b) or nx.has_path(kg, b, a):
                        return True
    return False


def extract_key_terms(text: str) -> Set[str]:
    """Extract key technical terms (nouns / proper nouns) from *text*."""
    nlp = _get_nlp()
    doc = nlp(text)
    return {
        token.lemma_.lower()
        for token in doc
        if token.pos_ in ("NOUN", "PROPN") and len(token.text) > 2
    }


def _check_entailment_simple(claim: str, evidence: str) -> bool:
    """Keyword-overlap proxy for textual entailment."""
    claim_words = set(claim.lower().split())
    evidence_words = set(evidence.lower().split())
    overlap = len(claim_words & evidence_words) / max(len(claim_words), 1)
    return overlap > 0.4


# ---------------------------------------------------------------------------
# MetricsComputer
# ---------------------------------------------------------------------------

class MetricsComputer:
    """Compute literature-grounded evaluation metrics for ARIAResult outputs.

    Each public method returns a ``Dict[str, float]`` of sub-scores and a
    composite score.

    Parameters
    ----------
    kg:
        A NetworkX DiGraph representing the PSP knowledge graph.
    embedding_model:
        A sentence-transformers model.  If *None*, one is loaded lazily.
    nli_model:
        An NLI pipeline for citation-claim entailment.  Optional; if
        *None*, literature entailment will be skipped.
    """

    def __init__(
        self,
        kg: Optional[nx.DiGraph] = None,
        embedding_model=None,
        nli_model=None,
    ):
        self.kg = kg
        self.embedding_model = embedding_model
        self.nli_model = nli_model

    # -- private helpers ----------------------------------------------------

    def _embed(self, text: str):
        model = self.embedding_model or _get_embedding_model()
        return model.encode(text)

    def _cosine(self, vec_a, vec_b) -> float:
        return float(cosine_similarity([vec_a], [vec_b])[0][0])

    # -- public metric methods ----------------------------------------------

    def causal_coherence(
        self,
        output: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> Dict[str, float]:
        """Measure causal coherence through intervention consistency,
        counterfactual reasoning, mechanistic modularity, and PSP chain
        validity.

        Grounded in Pearl (2019), Schölkopf et al. (2021), Geiger et al.
        (2023).
        """
        scores: Dict[str, float] = {}
        processing = output.get("processing_conditions", {})
        structure = output.get("structure", {})
        properties = output.get("predicted_properties", {})

        mech = output.get("mechanistic_explanation", {})
        if isinstance(mech, dict):
            cot = mech.get("chain_of_thought", [])
        else:
            cot = []

        # 1. Intervention consistency  (Pearl's do-calculus)
        causal_edges = extract_causal_edges(cot, self.embedding_model)
        intervention_score = 0.0
        if self.kg and causal_edges:
            for source, target, mechanism in causal_edges:
                if verify_causal_edge_in_kg(self.kg, source, target, mechanism):
                    intervention_score += 1.0
            intervention_score /= max(len(causal_edges), 1)
        scores["intervention_consistency"] = intervention_score

        # 2. Counterfactual reasoning  (Pearl Level 3)
        alternatives = mech.get("alternative_mechanisms", "") if isinstance(mech, dict) else ""
        counterfactual_score = 0.0
        if alternatives and len(alternatives) > 20:
            cf_emb = self._embed(alternatives)
            primary_emb = self._embed(
                mech.get("primary_mechanism", "") if isinstance(mech, dict) else ""
            )
            similarity = self._cosine(cf_emb, primary_emb)
            if 0.3 < similarity < 0.7:
                counterfactual_score = 0.8
                if "different" in alternatives.lower() or "instead" in alternatives.lower():
                    counterfactual_score = 1.0
        scores["counterfactual_reasoning"] = counterfactual_score

        # 3. Mechanistic modularity  (Schölkopf)
        modularity_score = 0.0
        if isinstance(mech, dict) and cot:
            causal_markers = [
                "leads to", "causes", "results in", "enables", "produces",
            ]
            has_clear_structure = all(
                any(marker in step.lower() for marker in causal_markers)
                for step in cot
                if isinstance(step, str)
            )
            if has_clear_structure:
                modularity_score = 0.5
            quant = mech.get("quantitative_estimates", {})
            if quant and len(quant) > 0:
                modularity_score += 0.3
            if "mechanism" in mech.get("primary_mechanism", "").lower():
                modularity_score += 0.2
        scores["mechanistic_modularity"] = min(modularity_score, 1.0)

        # 4. PSP chain validity
        psp_score = 0.0
        has_processing = bool(processing)
        has_structure = bool(structure)
        has_properties = bool(properties)
        if has_processing and has_structure and has_properties:
            psp_score = 0.4
            p_to_s = any(
                "processing" in step.lower() and "structure" in step.lower()
                for step in cot
                if isinstance(step, str)
            )
            s_to_prop = any(
                "structure" in step.lower()
                and any(
                    p in step.lower()
                    for p in ["property", "conductivity", "carrier", "mobility"]
                )
                for step in cot
                if isinstance(step, str)
            )
            if p_to_s:
                psp_score += 0.3
            if s_to_prop:
                psp_score += 0.3
        scores["psp_chain_validity"] = psp_score

        # Composite
        weights = {
            "intervention_consistency": 0.35,
            "counterfactual_reasoning": 0.25,
            "mechanistic_modularity": 0.25,
            "psp_chain_validity": 0.15,
        }
        scores["causal_coherence_score"] = float(
            np.clip(sum(scores[k] * weights[k] for k in weights), 0, 1)
        )
        return scores

    def source_grounding(
        self,
        output: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> float:
        """Measure quality of external grounding through KG verification,
        literature entailment, multi-hop reasoning, and source diversity.

        Grounded in FEVER (Thorne et al. 2018) and GopherCite (Menick 2022).

        Returns the composite ``source_grounding_score`` in [0, 1].
        """
        scores: Dict[str, float] = {}
        kg_paths = output.get("kg_paths_used", 0)
        lit_evidence = output.get("literature_evidence", [])
        lit_papers = output.get("literature_papers", 0)

        mech = output.get("mechanistic_explanation", {})
        primary_mech = mech.get("primary_mechanism", "") if isinstance(mech, dict) else ""

        # 1. KG path verification
        if self.kg and kg_paths > 0:
            claims = extract_atomic_claims(primary_mech)
            grounded = sum(
                1 for c in claims if verify_claim_in_kg(self.kg, c, self.embedding_model)
            )
            kg_verification = grounded / max(len(claims), 1)
        else:
            kg_verification = 0.0
        scores["kg_verification"] = kg_verification

        # 2. Literature entailment
        if lit_papers > 0 and lit_evidence and self.nli_model is not None:
            entailment_scores: List[float] = []
            for evidence in lit_evidence[:5]:
                result = self.nli_model(f"{evidence} [SEP] {primary_mech}")
                if result[0]["label"] == "ENTAILMENT":
                    entailment_scores.append(result[0]["score"])
                else:
                    entailment_scores.append(0.0)
            lit_entailment = float(np.mean(entailment_scores)) if entailment_scores else 0.0
            # Penalise over-citation
            citation_penalty = min(0.2, (lit_papers - 10) * 0.02) if lit_papers > 10 else 0.0
            lit_quality = max(0.0, lit_entailment - citation_penalty)
        else:
            lit_quality = 0.0
        scores["literature_entailment"] = lit_quality

        # 3. Multi-hop reasoning verification
        if isinstance(mech, dict):
            cot = mech.get("chain_of_thought", [])
        else:
            cot = []
        if isinstance(cot, list) and len(cot) >= 2:
            grounded_steps = 0
            for step in cot:
                if not isinstance(step, str):
                    continue
                if (self.kg and verify_claim_in_kg(self.kg, step, self.embedding_model)) or (
                    lit_evidence
                    and any(_check_entailment_simple(step, ev) for ev in lit_evidence[:5])
                ):
                    grounded_steps += 1
            multihop = grounded_steps / len(cot)
        else:
            multihop = 0.0
        scores["multihop_grounding"] = multihop

        # 4. Source diversity
        if lit_evidence and len(lit_evidence) > 1:
            embeddings = self._embed(lit_evidence[:5])
            if embeddings.ndim == 1:
                diversity = 0.0
            else:
                sims = cosine_similarity(embeddings)
                avg_sim = (sims.sum() - len(sims)) / (len(sims) * (len(sims) - 1) + 1e-9)
                diversity = 1.0 - min(avg_sim, 1.0)
        else:
            diversity = 0.0
        scores["source_diversity"] = diversity

        # Composite
        weights = {
            "kg_verification": 0.35,
            "literature_entailment": 0.35,
            "multihop_grounding": 0.20,
            "source_diversity": 0.10,
        }
        return float(np.clip(sum(scores[k] * weights[k] for k in weights), 0, 1))

    def internal_validity(self, output: Dict[str, Any]) -> float:
        """Measure faithfulness and logical consistency of explanations.

        Grounded in Wiegreffe & Marasović (2021), Yeh et al. (2023), and
        Lanham et al. (2023).

        Returns the composite ``internal_validity_score`` in [0, 1].
        """
        scores: Dict[str, float] = {}
        mech = output.get("mechanistic_explanation", {})
        if not isinstance(mech, dict):
            return 0.0

        primary_mech = mech.get("primary_mechanism", "")
        cot = mech.get("chain_of_thought", [])
        prediction = output.get("predicted_properties", {})

        # 1. Sufficiency test (explanation -> prediction)
        sufficiency = 0.0
        if primary_mech and prediction:
            pred_values = " ".join(str(v) for v in prediction.values())
            expl_emb = self._embed(primary_mech)
            pred_emb = self._embed(pred_values)
            semantic_alignment = self._cosine(expl_emb, pred_emb)
            if semantic_alignment > 0.5:
                sufficiency = 0.7
            if any(prop_key in primary_mech.lower() for prop_key in prediction):
                sufficiency = min(1.0, sufficiency + 0.3)
        scores["sufficiency"] = sufficiency

        # 2. Comprehensiveness test
        comprehensiveness = 0.0
        if cot and len(cot) >= 2:
            step_pairs_connected = 0
            for i in range(len(cot) - 1):
                if not isinstance(cot[i], str) or not isinstance(cot[i + 1], str):
                    continue
                entities_i = extract_key_terms(cot[i])
                entities_next = extract_key_terms(cot[i + 1])
                if entities_i & entities_next:
                    step_pairs_connected += 1
            comprehensiveness = step_pairs_connected / (len(cot) - 1) if len(cot) > 1 else 0.0
        scores["comprehensiveness"] = comprehensiveness

        # 3. Logical consistency
        consistency = 1.0
        if cot:
            negation_words = ["not", "however", "but", "although", "despite", "contrary"]
            contradiction_count = 0
            primary_emb = self._embed(primary_mech)
            for step in cot:
                if not isinstance(step, str):
                    continue
                if any(neg in step.lower() for neg in negation_words):
                    step_emb = self._embed(step)
                    if self._cosine(step_emb, primary_emb) > 0.6:
                        contradiction_count += 1
            consistency = max(0.0, 1.0 - contradiction_count * 0.3)
        scores["logical_consistency"] = consistency

        # 4. Mechanistic precision
        precision = 0.0
        quant_estimates = mech.get("quantitative_estimates", {})
        if quant_estimates:
            precision += 0.4
            has_units = any(
                any(unit in str(v).lower() for unit in ["cm", "ev", "k", "mol", "pa", "s"])
                for v in quant_estimates.values()
            )
            if has_units:
                precision += 0.3
        mechanism_terms = [
            "substitution", "doping", "defect", "phonon", "electron",
            "diffusion", "segregation", "precipitation",
        ]
        if any(term in primary_mech.lower() for term in mechanism_terms):
            precision += 0.3
        scores["mechanistic_precision"] = min(precision, 1.0)

        # 5. Forward simulation
        simulation = 0.0
        if len(cot) >= 3:
            testable_keywords = [
                "concentration", "temperature", "size", "thickness",
                "density", "composition", "phase", "crystal",
            ]
            middle_steps = cot[1:-1]
            testable = sum(
                1
                for step in middle_steps
                if isinstance(step, str) and any(kw in step.lower() for kw in testable_keywords)
            )
            simulation = min(1.0, testable / len(middle_steps)) if middle_steps else 0.0
        scores["forward_simulation"] = simulation

        weights = {
            "sufficiency": 0.30,
            "comprehensiveness": 0.20,
            "logical_consistency": 0.25,
            "mechanistic_precision": 0.15,
            "forward_simulation": 0.10,
        }
        return float(np.clip(sum(scores[k] * weights[k] for k in weights), 0, 1))

    def psp_consistency(self, output: Dict[str, Any]) -> float:
        """Check PSP (Processing -> Structure -> Property) chain completeness.

        Returns a score in [0, 1] measuring whether the output contains a
        complete and well-connected PSP causal chain.
        """
        processing = output.get("processing_conditions", {})
        structure = output.get("structure", {})
        properties = output.get("predicted_properties", {})
        mech = output.get("mechanistic_explanation", {})
        cot = mech.get("chain_of_thought", []) if isinstance(mech, dict) else []

        score = 0.0

        # All three components present
        if processing and structure and properties:
            score += 0.4
        elif processing and properties:
            score += 0.2

        # Causal links in chain-of-thought
        if cot and isinstance(cot, list):
            p_to_s = any(
                "processing" in step.lower() and "structure" in step.lower()
                for step in cot
                if isinstance(step, str)
            )
            s_to_p = any(
                "structure" in step.lower()
                and any(
                    kw in step.lower()
                    for kw in ["property", "conductivity", "carrier", "mobility"]
                )
                for step in cot
                if isinstance(step, str)
            )
            if p_to_s:
                score += 0.3
            if s_to_p:
                score += 0.3

        return float(np.clip(score, 0, 1))

    def compute_all(
        self,
        output: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> Dict[str, float]:
        """Run all metrics and return a flat dictionary of scores.

        Includes sub-scores from each metric category as well as composite
        scores.
        """
        results: Dict[str, float] = {}

        # Causal coherence (includes sub-scores)
        causal_scores = self.causal_coherence(output, ground_truth)
        results.update(causal_scores)

        # Source grounding
        results["source_grounding_score"] = self.source_grounding(output, ground_truth)

        # Internal validity
        results["internal_validity_score"] = self.internal_validity(output)

        # PSP consistency
        results["psp_consistency_score"] = self.psp_consistency(output)

        # Overall composite
        results["overall_score"] = float(np.mean([
            results["causal_coherence_score"],
            results["source_grounding_score"],
            results["internal_validity_score"],
            results["psp_consistency_score"],
        ]))

        return results