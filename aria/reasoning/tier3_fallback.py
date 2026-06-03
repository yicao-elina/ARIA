"""
Tier 3 Fallback Reasoner -- pure LLM with no KG evidence.

Used when no knowledge-graph match is available (baseline mode) or as a
fallback when higher tiers fail.  Also serves as the standalone baseline
for ablation studies.

Author: ARIA Team
"""

import json
import logging
from typing import Any, Dict

from aria.types import ReasoningTier
from aria.reasoning.prompts import (
    TIER3_FORWARD_PROMPT,
    TIER3_INVERSE_PROMPT,
    BASELINE_FORWARD_PROMPT,
    BASELINE_INVERSE_PROMPT,
)

logger = logging.getLogger(__name__)


class Tier3FallbackReasoner:
    """Tier 3: Pure LLM fallback (no KG evidence).

    In baseline mode, uses the richer BASELINE_FORWARD/INVERSE_PROMPT
    templates.  In aria mode (as a fallback from Tiers 1/2), uses the
    shorter TIER3_FORWARD/INVERSE_PROMPT templates.

    Parameters
    ----------
    llm_client
        An object exposing ``generate_json(prompt) -> dict``.
    mode : str
        ``"baseline"`` for the standalone baseline variant,
        ``"aria"`` for the tier-3 fallback variant.
    """

    def __init__(self, llm_client, mode: str = "aria") -> None:
        self.llm = llm_client
        self.mode = mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forward(
        self,
        synthesis_inputs: Dict[str, Any],
        llm_client=None,
    ) -> Dict[str, Any]:
        """Predict material properties from synthesis conditions using pure
        LLM knowledge (no KG).

        Parameters
        ----------
        synthesis_inputs : dict
            Synthesis conditions, e.g. ``{"method": "CVD", "temperature_c": 750}``.
        llm_client : optional
            Override the default LLM client for this call.

        Returns
        -------
        dict
            Prediction dict with ``predicted_properties``, ``tier``,
            ``confidence``, ``reasoning_type``.
        """
        llm = llm_client or self.llm
        logger.info("Tier 3 Fallback: forward prediction (no KG)")

        if self.mode == "baseline":
            return self._baseline_forward(synthesis_inputs, llm)
        return self._aria_forward(synthesis_inputs, llm)

    def inverse(
        self,
        desired_properties: Dict[str, Any],
        llm_client=None,
    ) -> Dict[str, Any]:
        """Design synthesis conditions for desired properties using pure
        LLM knowledge (no KG).

        Parameters
        ----------
        desired_properties : dict
            Target material properties.
        llm_client : optional

        Returns
        -------
        dict
            Synthesis recommendation dict with
            ``suggested_synthesis_conditions``.
        """
        llm = llm_client or self.llm
        logger.info("Tier 3 Fallback: inverse design (no KG)")

        if self.mode == "baseline":
            return self._baseline_inverse(desired_properties, llm)
        return self._aria_inverse(desired_properties, llm)

    # ------------------------------------------------------------------
    # Baseline mode (richer prompts for ablation study)
    # ------------------------------------------------------------------

    @staticmethod
    def _baseline_forward(inputs: Dict[str, Any], llm) -> Dict[str, Any]:
        """Standalone baseline forward prediction."""
        input_keywords = [str(v) for v in inputs.values() if v is not None]
        query_string = " and ".join(input_keywords)

        prompt = BASELINE_FORWARD_PROMPT.format(
            query_string=query_string,
            synthesis_inputs=json.dumps(inputs, indent=2),
        )

        try:
            response = llm.generate_json(prompt, temperature=0.0)
            if "reasoning_type" not in response:
                response["reasoning_type"] = "baseline_llm"
            response["tier"] = ReasoningTier.FALLBACK.value
            response["kg_paths_used"] = 0
            return response
        except Exception as exc:
            logger.error("Baseline forward failed: %s", exc)
            return {
                "predicted_properties": {},
                "reasoning": f"Error: {exc}",
                "confidence": 0.0,
                "tier": ReasoningTier.FALLBACK.value,
                "reasoning_type": "baseline_llm_error",
            }

    @staticmethod
    def _baseline_inverse(inputs: Dict[str, Any], llm) -> Dict[str, Any]:
        """Standalone baseline inverse design."""
        property_keywords = [str(v) for v in inputs.values() if v is not None]
        query_string = " and ".join(property_keywords)

        prompt = BASELINE_INVERSE_PROMPT.format(
            query_string=query_string,
            desired_properties=json.dumps(inputs, indent=2),
        )

        try:
            response = llm.generate_json(prompt, temperature=0.0)
            if "reasoning_type" not in response:
                response["reasoning_type"] = "baseline_llm_inverse"
            response["tier"] = ReasoningTier.FALLBACK.value
            response["kg_paths_used"] = 0
            return response
        except Exception as exc:
            logger.error("Baseline inverse failed: %s", exc)
            return {
                "suggested_synthesis_conditions": {},
                "reasoning": f"Error: {exc}",
                "confidence": 0.0,
                "tier": ReasoningTier.FALLBACK.value,
                "reasoning_type": "baseline_llm_inverse_error",
            }

    # ------------------------------------------------------------------
    # ARIA fallback mode (shorter prompts)
    # ------------------------------------------------------------------

    @staticmethod
    def _aria_forward(inputs: Dict[str, Any], llm) -> Dict[str, Any]:
        """Short-prompt fallback from Tiers 1/2."""
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
            logger.error("Tier 3 forward fallback failed: %s", exc)
            return {
                "error": str(exc),
                "confidence": 0.0,
                "tier": ReasoningTier.FALLBACK.value,
                "reasoning_type": "error",
            }

    @staticmethod
    def _aria_inverse(inputs: Dict[str, Any], llm) -> Dict[str, Any]:
        """Short-prompt inverse fallback from Tiers 1/2."""
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
            logger.error("Tier 3 inverse fallback failed: %s", exc)
            return {
                "error": str(exc),
                "confidence": 0.0,
                "tier": ReasoningTier.FALLBACK.value,
                "reasoning_type": "error",
            }