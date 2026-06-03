"""ARIA reasoning module -- tier dispatch, prompts, and literature search."""

from aria.reasoning.prompts import (
    TIER1_FORWARD_PROMPT,
    TIER1_INVERSE_PROMPT,
    TIER2_FORWARD_PROMPT,
    TIER2_INVERSE_PROMPT,
    TIER3_FORWARD_PROMPT,
    TIER3_INVERSE_PROMPT,
    BASELINE_FORWARD_PROMPT,
    BASELINE_INVERSE_PROMPT,
    NAIVE_KG_FORWARD_PROMPT,
    NAIVE_KG_INVERSE_PROMPT,
    COT_REASONING_PROMPT,
)
from aria.reasoning.tier1_direct import Tier1DirectReasoner
from aria.reasoning.tier2_analogical import Tier2AnalogicalReasoner
from aria.reasoning.tier3_fallback import Tier3FallbackReasoner
from aria.reasoning.router import ReasoningRouter, RoutingDecision
from aria.reasoning.literature import LiteratureSearcher

__all__ = [
    # Prompts
    "TIER1_FORWARD_PROMPT",
    "TIER1_INVERSE_PROMPT",
    "TIER2_FORWARD_PROMPT",
    "TIER2_INVERSE_PROMPT",
    "TIER3_FORWARD_PROMPT",
    "TIER3_INVERSE_PROMPT",
    "BASELINE_FORWARD_PROMPT",
    "BASELINE_INVERSE_PROMPT",
    "NAIVE_KG_FORWARD_PROMPT",
    "NAIVE_KG_INVERSE_PROMPT",
    "COT_REASONING_PROMPT",
    # Reasoners
    "Tier1DirectReasoner",
    "Tier2AnalogicalReasoner",
    "Tier3FallbackReasoner",
    # Router
    "ReasoningRouter",
    "RoutingDecision",
    # Literature
    "LiteratureSearcher",
]