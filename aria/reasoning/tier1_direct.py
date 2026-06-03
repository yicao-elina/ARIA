"""
Tier 1 Direct Reasoner -- exact KG path matching.

Uses causal pathways found by direct keyword search in the knowledge
graph.  Falls back to Tier 3 when LLM calls fail.

Author: ARIA Team
"""

import json
import logging
from typing import Any, Dict, List, Optional

from aria.types import ReasoningTier
from aria.reasoning.prompts import (
    TIER1_FORWARD_PROMPT,
    TIER1_INVERSE_PROMPT,
    TIER3_FORWARD_PROMPT,
    TIER3_INVERSE_PROMPT,
)

logger = logging.getLogger(__name__)


class Tier1DirectReasoner:
    """Tier 1: Direct causal-path reasoning with exact KG matches.

    Parameters
    ----------
    llm_client
        An object exposing ``generate_json(prompt) -> dict`` and
        ``generate(prompt) -> str``.  This is the unified LLM backend
        (Ollama, OpenAI-compatible, etc.).
    """

    def __init__(self, llm_client) -> None:
        self.llm = llm_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forward(
        self,
        graph,                  # nx.DiGraph -- the KG
        synthesis_inputs: Dict[str, Any],
        paths: List[str],
        mechanisms: List[str],
        llm_client=None,
    ) -> Dict[str, Any]:
        """Predict material properties from synthesis conditions using
        direct causal pathways.

        Parameters
        ----------
        graph : nx.DiGraph
            Knowledge graph (used for provenance metadata only here).
        synthesis_inputs : dict
            Synthesis conditions, e.g. ``{"method": "CVD", "temperature_c": 750}``.
        paths : list[str]
            Causal path strings, e.g. ``["A -> B -> C"]``.
        mechanisms : list[str]
            Mechanism quotes extracted from the paths.
        llm_client : optional
            Override the default LLM client for this call.

        Returns
        -------
        dict
            Prediction dict with ``predicted_properties``, ``tier``, etc.
        """
        llm = llm_client or self.llm
        logger.info("Tier 1 Direct: forward prediction (exact KG paths)")

        formatted_paths = "\n- ".join(paths)
        formatted_mechs = (
            "\n- ".join(mechanisms) if mechanisms else "No mechanisms available"
        )

        prompt = TIER1_FORWARD_PROMPT.format(
            synthesis_inputs=json.dumps(synthesis_inputs, indent=2),
            formatted_paths=formatted_paths,
            formatted_mechanisms=formatted_mechs,
        )

        try:
            response = llm.generate_json(prompt, temperature=0.0)
            response["tier"] = ReasoningTier.DIRECT.value
            response["reasoning_type"] = "direct_path"
            response["kg_paths_used"] = len(paths)
            if "mechanistic_explanation" in response:
                response["reasoning"] = json.dumps(response["mechanistic_explanation"])
            return response
        except Exception as exc:
            logger.error("Tier 1 forward failed: %s", exc)
            return self._fallback_forward(synthesis_inputs, llm)

    def inverse(
        self,
        graph,
        desired_properties: Dict[str, Any],
        paths: List[str],
        mechanisms: List[str],
        llm_client=None,
    ) -> Dict[str, Any]:
        """Design synthesis conditions for desired properties using direct
        (reverse) causal pathways.

        Parameters
        ----------
        graph : nx.DiGraph
        desired_properties : dict
            Target material properties.
        paths : list[str]
            Reverse causal paths found in the KG.
        mechanisms : list[str]
            Mechanism quotes extracted from the paths.
        llm_client : optional

        Returns
        -------
        dict
            Synthesis recommendation dict with ``suggested_synthesis_conditions``.
        """
        llm = llm_client or self.llm
        logger.info("Tier 1 Direct: inverse design (exact KG paths)")

        formatted_paths = "\n- ".join(paths)
        formatted_mechs = "\n- ".join(mechanisms) if mechanisms else "No mechanisms"

        prompt = TIER1_INVERSE_PROMPT.format(
            desired_properties=json.dumps(desired_properties, indent=2),
            formatted_paths=formatted_paths,
            formatted_mechanisms=formatted_mechs,
        )

        try:
            response = llm.generate_json(prompt, temperature=0.0)
            response["tier"] = ReasoningTier.DIRECT.value
            response["reasoning_type"] = "direct_inverse"
            response["kg_paths_used"] = len(paths)
            return response
        except Exception as exc:
            logger.error("Tier 1 inverse failed: %s", exc)
            return self._fallback_inverse(desired_properties, llm)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_forward(inputs: Dict[str, Any], llm) -> Dict[str, Any]:
        """Fall back to Tier 3 (baseline) when the LLM call fails."""
        prompt = TIER3_FORWARD_PROMPT.format(
            synthesis_inputs=json.dumps(inputs, indent=2),
        )
        try:
            response = llm.generate_json(prompt, temperature=0.0)
            response["tier"] = ReasoningTier.FALLBACK.value
            response["reasoning_type"] = "baseline_fallback"
            response["kg_paths_used"] = 0
            if "mechanistic_explanation" in response:
                response["reasoning"] = json.dumps(response["mechanistic_explanation"])
            return response
        except Exception as exc:
            logger.error("Tier 1 -> 3 fallback failed: %s", exc)
            return {
                "error": str(exc),
                "confidence": 0.0,
                "tier": ReasoningTier.FALLBACK.value,
                "reasoning_type": "error",
            }

    @staticmethod
    def _fallback_inverse(inputs: Dict[str, Any], llm) -> Dict[str, Any]:
        """Fall back to Tier 3 (baseline) for inverse design."""
        prompt = TIER3_INVERSE_PROMPT.format(
            desired_properties=json.dumps(inputs, indent=2),
        )
        try:
            response = llm.generate_json(prompt, temperature=0.0)
            response["tier"] = ReasoningTier.FALLBACK.value
            response["reasoning_type"] = "baseline_fallback_inverse"
            response["kg_paths_used"] = 0
            return response
        except Exception as exc:
            logger.error("Tier 1 -> 3 inverse fallback failed: %s", exc)
            return {
                "error": str(exc),
                "confidence": 0.0,
                "tier": ReasoningTier.FALLBACK.value,
                "reasoning_type": "error",
            }