"""
ARIA: Causal-Aware Reasoning for Materials Discovery.

ARIA is a causal evidence-gating framework that helps LLMs reason over
Processing-Structure-Property pathways for materials synthesis and property
prediction. Unlike standard RAG, ARIA activates retrieved evidence only
when it forms a causally complete PSP path.

Quick Start:
    >>> from aria import ARIAEngine, load_kg
    >>> kg = load_kg("data/aria_2d_kg_tiny.json")
    >>> engine = ARIAEngine(kg=kg, model="qwen2:7b", mode="aria")
    >>> result = engine.forward_predict(
    ...     material="MoS2",
    ...     processing={"temperature": "750C", "method": "CVD"},
    ...     target_property="carrier mobility"
    ... )
    >>> print(result.answer, result.tier, result.confidence)
"""

from aria.types import (
    ARIAResult,
    CausalTraceStep,
    ChainOfThought,
    EngineMode,
    KnowledgeSource,
    PSPRelationship,
    PSPType,
    ReasoningStep,
    ReasoningTier,
)

__version__ = "0.1.0"
__all__ = [
    "ARIAResult",
    "CausalTraceStep",
    "ChainOfThought",
    "EngineMode",
    "KnowledgeSource",
    "PSPRelationship",
    "PSPType",
    "ReasoningStep",
    "ReasoningTier",
]

# Lazy imports for heavy dependencies
def __getattr__(name):
    if name == "ARIAEngine":
        from aria.engine import ARIAEngine
        return ARIAEngine
    elif name == "load_kg":
        from aria.kg.graph_store import load_kg
        return load_kg
    elif name == "save_kg":
        from aria.kg.graph_store import save_kg
        return save_kg
    raise AttributeError(f"module 'aria' has no attribute {name!r}")