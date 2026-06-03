"""
ARIA type definitions.

Unified data types for the ARIA reasoning framework.
Every engine mode returns the same ARIAResult type,
enabling consistent comparison and evaluation.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any


class ReasoningTier(Enum):
    """Three-tier reasoning cascade for causal evidence activation."""
    DIRECT = 1       # Tier 1: exact PSP path match in KG
    ANALOGICAL = 2   # Tier 2: similarity-based analogical transfer
    FALLBACK = 3     # Tier 3: parametric LLM fallback (no KG evidence)


class EngineMode(Enum):
    """ARIA engine operating modes."""
    BASELINE = "baseline"           # Pure LLM (no KG)
    NAIVE_KG = "naive_kg"          # Simple KG + LLM concatenation
    ARIA = "aria"                   # 3-tier causal cascade (default)
    ARIA_SEARCH = "aria_search"     # 3-tier + literature search
    ARIA_FULL = "aria_full"         # 3-tier + literature + CoT transparency


class PSPType(Enum):
    """PSP (Processing-Structure-Property) edge types."""
    PROCESSING_TO_STRUCTURE = "Processing_to_Structure"
    STRUCTURE_TO_PROPERTY = "Structure_to_Property"
    PROCESSING_TO_PROPERTY = "Processing_to_Property"    # shortcut edge
    STRUCTURE_TO_STRUCTURE = "Structure_to_Structure"      # analogous materials
    PROCESSING_TO_PROCESSING = "Processing_to_Processing"  # process relations


@dataclass
class CausalTraceStep:
    """Single step in a PSP causal chain.

    Represents one link in the Processing -> Structure -> Property
    causal hierarchy that ARIA traces for each prediction.
    """
    processing: str              # e.g., "CVD temperature 750C"
    structure: str               # e.g., "improved crystallinity"
    property_: str               # e.g., "higher carrier mobility"
    evidence_text: Optional[str] = None    # Supporting evidence sentence
    evidence_doi: Optional[str] = None    # DOI of source paper
    confidence: float = 1.0                # Edge confidence [0, 1]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KnowledgeSource:
    """Track individual knowledge sources with metadata.

    Used in ARIA_FULL mode for chain-of-thought transparency
    and source attribution.
    """
    source_id: str
    content: str
    source_type: str    # "kg_node", "kg_edge", "kg_mechanism", "literature", "llm_baseline"
    confidence: float
    context: str
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReasoningStep:
    """Individual step in chain-of-thought reasoning."""
    step_id: str
    description: str
    evidence_sources: List[KnowledgeSource] = field(default_factory=list)
    reasoning_type: str = ""     # "retrieval", "synthesis", "validation", "inference", "search"
    confidence: float = 0.0
    intermediate_conclusion: str = ""

    def to_dict(self) -> dict:
        return {
            'step_id': self.step_id,
            'description': self.description,
            'evidence_sources': [s.to_dict() for s in self.evidence_sources],
            'reasoning_type': self.reasoning_type,
            'confidence': self.confidence,
            'intermediate_conclusion': self.intermediate_conclusion,
        }


@dataclass
class ChainOfThought:
    """Complete reasoning chain with source attribution."""
    query_context: Dict = field(default_factory=dict)
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    final_reasoning: str = ""
    final_result: Dict = field(default_factory=dict)
    confidence_breakdown: Dict = field(default_factory=dict)
    source_attribution: Dict = field(default_factory=dict)
    tier: int = 0
    kg_paths_used: int = 0
    literature_papers_used: int = 0

    def to_dict(self) -> dict:
        return {
            'query_context': self.query_context,
            'reasoning_steps': [step.to_dict() for step in self.reasoning_steps],
            'final_reasoning': self.final_reasoning,
            'final_result': self.final_result,
            'confidence_breakdown': self.confidence_breakdown,
            'source_attribution': self.source_attribution,
            'tier': self.tier,
            'kg_paths_used': self.kg_paths_used,
            'literature_papers_used': self.literature_papers_used,
        }


@dataclass
class ARIAResult:
    """Unified output for all ARIA engine modes.

    Every mode (baseline, naive_kg, aria, aria_search, aria_full)
    returns this same structure, enabling consistent comparison
    and evaluation across modes.
    """
    # Core prediction
    answer: Dict[str, Any]
    tier: ReasoningTier
    confidence: float                      # 0.0-1.0
    reasoning_type: str                    # "direct_path", "transfer_learning", "baseline_fallback", etc.

    # Causal trace (PSP chain)
    causal_trace: List[CausalTraceStep] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)

    # KG provenance
    kg_paths_used: int = 0
    kg_paths: List[str] = field(default_factory=list)

    # Literature (ARIA_SEARCH / ARIA_FULL only)
    literature_papers: List[Dict] = field(default_factory=list)

    # Source attribution (ARIA_FULL only)
    source_attribution: Dict[str, Any] = field(default_factory=dict)
    chain_of_thought: Optional[ChainOfThought] = None

    # Metadata
    mode: str = ""
    model: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        result = {
            'answer': self.answer,
            'tier': self.tier.value,
            'confidence': self.confidence,
            'reasoning_type': self.reasoning_type,
            'causal_trace': [step.to_dict() for step in self.causal_trace],
            'missing_evidence': self.missing_evidence,
            'kg_paths_used': self.kg_paths_used,
            'kg_paths': self.kg_paths,
            'literature_papers': self.literature_papers,
            'source_attribution': self.source_attribution,
            'mode': self.mode,
            'model': self.model,
            'latency_ms': self.latency_ms,
        }
        if self.chain_of_thought is not None:
            result['chain_of_thought'] = self.chain_of_thought.to_dict()
        return result

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


@dataclass
class PSPRelationship:
    """A single edge in the PSP causal knowledge graph.

    Each relationship encodes a causal link in the
    Processing-Structure-Property hierarchy, with provenance
    metadata for evidence tracking.
    """
    source: str                          # Cause node (e.g., "growth_temperature:750C")
    relation: str                         # "increases", "decreases", "induces", etc.
    target: str                          # Effect node (e.g., "crystallinity")
    psp_type: str                        # PSPType value
    material: str = ""                   # Material (e.g., "MoS2")
    evidence_text: Optional[str] = None   # Supporting evidence sentence
    paper_doi: Optional[str] = None       # DOI of source paper
    confidence: float = 1.0               # 0.0-1.0
    curation: str = "extracted"           # "expert_verified", "extracted", "normalized"
    relationship_id: Optional[str] = None # Unique identifier

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_legacy(cls, data: dict) -> "PSPRelationship":
        """Convert from the legacy combined_doping_data.json format.

        The legacy format uses fields like:
        - cause_parameter, effect_on_doping, affected_property
        - mechanism_quote, confidence_level, source_file
        """
        return cls(
            source=data.get("cause_parameter", ""),
            relation=_infer_relation(data.get("effect_on_doping", "")),
            target=data.get("affected_property", data.get("effect_on_doping", "")),
            psp_type=_infer_psp_type(
                data.get("cause_parameter", ""),
                data.get("affected_property", ""),
            ),
            material=_infer_material(data.get("source_file", "")),
            evidence_text=data.get("mechanism_quote"),
            paper_doi=data.get("paper_doi"),
            confidence=_parse_confidence(data.get("confidence_level", "")),
            curation="extracted",
            relationship_id=data.get("relationship_id"),
        )


def _infer_relation(effect_text: str) -> str:
    """Infer the relation type from effect text."""
    text = effect_text.lower()
    if any(w in text for w in ["increases", "improves", "enhances", "promotes", "raises"]):
        return "increases"
    elif any(w in text for w in ["decreases", "reduces", "suppresses", "lowers", "diminishes"]):
        return "decreases"
    elif any(w in text for w in ["induces", "causes", "leads to", "produces", "creates"]):
        return "induces"
    elif any(w in text for w in ["inhibits", "prevents", "blocks", "hinders"]):
        return "inhibits"
    else:
        return "affects"


def _infer_psp_type(cause: str, effect: str) -> str:
    """Infer the PSP layer type from cause and effect."""
    processing_kw = ["temperature", "pressure", "time", "atmosphere", "substrate",
                     "precursor", "method", "annealing", "doping", "growth", "cvd",
                     "mocvd", "sputtering", "catalyst", "solvent", "concentration"]
    structure_kw = ["crystallinity", "phase", "morphology", "defect", "grain",
                    "layer", "vacancy", "stoichiometry", "crystal", "strain",
                    "doping_level", "thickness", "orientation", "grain_size"]
    property_kw = ["mobility", "band_gap", "conductivity", "carrier", "resistance",
                   "photoluminescence", "absorption", "emission", "ferromagnetic",
                   "hall", "transconductance", "on/off"]

    cause_lower = cause.lower()
    effect_lower = effect.lower()

    cause_is_processing = any(kw in cause_lower for kw in processing_kw)
    cause_is_structure = any(kw in cause_lower for kw in structure_kw)
    effect_is_structure = any(kw in effect_lower for kw in structure_kw)
    effect_is_property = any(kw in effect_lower for kw in property_kw)

    if cause_is_processing and effect_is_structure:
        return PSPType.PROCESSING_TO_STRUCTURE.value
    elif cause_is_structure and effect_is_property:
        return PSPType.STRUCTURE_TO_PROPERTY.value
    elif cause_is_processing and effect_is_property:
        return PSPType.PROCESSING_TO_PROPERTY.value
    elif cause_is_structure and effect_is_structure:
        return PSPType.STRUCTURE_TO_STRUCTURE.value
    elif cause_is_processing and not effect_is_structure and not effect_is_property:
        return PSPType.PROCESSING_TO_STRUCTURE.value  # default for processing inputs
    else:
        return PSPType.PROCESSING_TO_PROPERTY.value  # default


def _infer_material(source_file: str) -> str:
    """Infer material name from source file name."""
    if not source_file:
        return ""
    source_lower = source_file.lower()
    materials = ["mos2", "ws2", "wse2", "mose2", "mote2", "wte2",
                 "graphene", "hbn", "bn", "black_phosphorus", "bp"]
    for mat in materials:
        if mat in source_lower:
            return mat.upper() if len(mat) <= 4 else mat
    return ""


def _parse_confidence(confidence_level: str) -> float:
    """Parse confidence level string to float."""
    if not confidence_level:
        return 0.7
    level_lower = confidence_level.lower()
    if "experimentally" in level_lower or "proven" in level_lower:
        return 0.95
    elif "high" in level_lower or "strong" in level_lower:
        return 0.85
    elif "moderate" in level_lower or "medium" in level_lower:
        return 0.7
    elif "low" in level_lower or "weak" in level_lower:
        return 0.5
    elif "theoretical" in level_lower or "predicted" in level_lower:
        return 0.6
    else:
        return 0.7