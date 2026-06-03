"""
Tier 2 Analogical Reasoner -- similarity-based transfer learning.

When no exact KG path is found but a semantically similar node exists,
Tier 2 adapts the analogous knowledge to the target case.

Author: ARIA Team
"""

import json
import logging
from typing import Any, Dict, List, Optional

from aria.types import ReasoningTier
from aria.reasoning.prompts import (
    TIER2_FORWARD_PROMPT,
    TIER2_INVERSE_PROMPT,
    TIER3_FORWARD_PROMPT,
    TIER3_INVERSE_PROMPT,
)

logger = logging.getLogger(__name__)


class Tier2AnalogicalReasoner:
    """Tier 2: Analogical / transfer-learning reasoning.

    Uses embedding similarity to find the closest KG node and then adapts
    that node's causal pathways to the target query.

    Parameters
    ----------
    llm_client
        An object exposing ``generate_json(prompt) -> dict``.
    """

    def __init__(self, llm_client) -> None:
        self.llm = llm_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forward(
        self,
        graph,                       # nx.DiGraph
        synthesis_inputs: Dict[str, Any],
        paths: List[str],
        mechanisms: List[str],
        similar_node: str,
        similarity: float,
        llm_client=None,
    ) -> Dict[str, Any]:
        """Predict properties via analogical transfer.

        Parameters
        ----------
        graph : nx.DiGraph
        synthesis_inputs : dict
            Synthesis conditions for the target material.
        paths : list[str]
            Causal paths from the analogous (similar) node.
        mechanisms : list[str]
            Mechanism quotes from those paths.
        similar_node : str
            Name of the closest KG node.
        similarity : float
            Cosine similarity score to the similar node.
        llm_client : optional

        Returns
        -------
        dict
            Prediction dict with ``predicted_properties``, ``tier``,
            ``similarity_score``, ``analogous_node``.
        """
        llm = llm_client or self.llm
        logger.info(
            "Tier 2 Analogical: forward (similar_node=%s, similarity=%.3f)",
            similar_node,
            similarity,
        )

        formatted_path = paths[0] if paths else "No path found"
        formatted_mechs = (
            "\n- ".join(mechanisms) if mechanisms else "No mechanisms available"
        )

        prompt = TIER2_FORWARD_PROMPT.format(
            synthesis_inputs=json.dumps(synthesis_inputs, indent=2),
            similar_node=similar_node,
            similarity=similarity,
            formatted_path=formatted_path,
            formatted_mechanisms=formatted_mechs,
            target_case=json.dumps(synthesis_inputs),
        )

        try:
            response = llm.generate_json(prompt, temperature=0.0)
            response["tier"] = ReasoningTier.ANALOGICAL.value
            response["reasoning_type"] = "transfer_learning"
            response["similarity_score"] = similarity
            response["analogous_node"] = similar_node
            if "mechanistic_explanation" in response:
                response["reasoning"] = json.dumps(response["mechanistic_explanation"])
            return response
        except Exception as exc:
            logger.error("Tier 2 forward failed: %s", exc)
            return self._fallback_forward(synthesis_inputs, llm)

    def inverse(
        self,
        graph,
        desired_properties: Dict[str, Any],
        paths: List[str],
        mechanisms: List[str],
        similar_node: str,
        similarity: float,
        embedding_distance: float = 0.0,
        llm_client=None,
    ) -> Dict[str, Any]:
        """Design synthesis via analogical transfer (inverse direction).

        Parameters
        ----------
        graph : nx.DiGraph
        desired_properties : dict
            Target material properties.
        paths : list[str]
            Analogous reverse causal paths.
        mechanisms : list[str]
            Mechanism quotes from those paths.
        similar_node : str
            Name of the closest property node in the KG.
        similarity : float
            Cosine similarity to the similar node.
        embedding_distance : float
            1 - cosine_similarity (for transparency in the prompt).
        llm_client : optional

        Returns
        -------
        dict
            Synthesis recommendation dict.
        """
        llm = llm_client or self.llm
        logger.info(
            "Tier 2 Analogical: inverse (similar_node=%s, similarity=%.3f)",
            similar_node,
            similarity,
        )

        formatted_path = paths[0] if paths else "No path"
        formatted_mechs = "\n- ".join(mechanisms) if mechanisms else "No mechanisms"

        prompt = TIER2_INVERSE_PROMPT.format(
            desired_properties=json.dumps(desired_properties, indent=2),
            similar_node=similar_node,
            similarity=similarity,
            embedding_distance=embedding_distance,
            formatted_path=formatted_path,
            formatted_mechanisms=formatted_mechs,
        )

        try:
            response = llm.generate_json(prompt, temperature=0.0)
            response["tier"] = ReasoningTier.ANALOGICAL.value
            response["reasoning_type"] = "transfer_inverse"
            response["similarity_score"] = similarity
            response["embedding_distance"] = embedding_distance
            return response
        except Exception as exc:
            logger.error("Tier 2 inverse failed: %s", exc)
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
            logger.error("Tier 2 -> 3 forward fallback failed: %s", exc)
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
            logger.error("Tier 2 -> 3 inverse fallback failed: %s", exc)
            return {
                "error": str(exc),
                "confidence": 0.0,
                "tier": ReasoningTier.FALLBACK.value,
                "reasoning_type": "error",
            }