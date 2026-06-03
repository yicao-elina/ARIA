"""
ARIA LLM-as-a-Judge evaluation.

Generalised from ``OllamaJudge`` to support multiple LLM backends
(Ollama, OpenAI-compatible APIs, etc.).  Scores predictions on four
domain-specific rubrics:

  1. Processing Feasibility  (0--40)
  2. Structure Emergence      (0--30)
  3. Property Consistency     (0--20)
  4. Causal PSP Reasoning     (0--10)

Ported from ``ollama_judge.py``.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metric rubric definitions
# ---------------------------------------------------------------------------

METRICS: Dict[str, Dict[str, Any]] = {
    "processing_feasibility": {
        "name": "Processing Feasibility",
        "max_score": 40,
        "description": (
            "Thermodynamic & kinetic viability of predicted processing conditions"
        ),
        "rubric": """
Score 35-40: All conditions thermodynamically/kinetically viable, realistic equipment
  - Temperature ranges appropriate for material phase stability
  - Pressure conditions compatible with synthesis method
  - Time scales realistic for defect formation/annealing
  - Atmosphere correct for doping/oxidation control
  - Equipment feasible in typical labs
  - No safety hazards or unrealistic conditions

Score 25-34: Minor feasibility issues
  - Slightly high/low temperature (but within possible range)
  - Extended time scales (but not impossible)
  - Common equipment with minor modifications

Score 15-24: Significant issues
  - Wrong atmosphere for desired outcome
  - Unrealistic pressure for method
  - Temperature incompatible with substrate/precursor

Score 0-14: Fundamentally impossible
  - Violates phase diagram or thermodynamic constraints
  - Conditions destroy material before defects form
  - Physically impossible parameter combinations
""",
    },
    "structure_emergence": {
        "name": "Structure Emergence",
        "max_score": 30,
        "description": "Accuracy of predicted structural outcomes from processing",
        "rubric": """
Score 25-30: Excellent structural prediction
  - Correct defect type (vacancy, substitution, interstitial)
  - Realistic defect density/concentration
  - Accurate lattice strain effects
  - Correct stacking order (for heterostructures)
  - Phase purity considerations addressed
  - Crystal structure/symmetry preserved or correctly modified

Score 18-24: Good with minor inaccuracies
  - Correct defect type but density slightly off
  - Strain magnitude imprecise but directionally correct
  - Missing minor structural details

Score 10-17: Partially correct
  - Right defect family but wrong specific type
  - Major uncertainty in defect density
  - Incomplete structural description

Score 0-9: Incorrect or major errors
  - Wrong defect type for processing conditions
  - Structurally impossible outcomes
  - Ignores symmetry constraints
""",
    },
    "property_consistency": {
        "name": "Property Consistency",
        "max_score": 20,
        "description": "Coherence between predicted properties and structure/processing",
        "rubric": """
Score 17-20: Fully consistent
  - Electronic properties (band gap, carrier type, conductivity) match structure
  - Mechanical properties (strength, modulus) consistent with defect density
  - Optical properties aligned with electronic structure
  - Magnetic properties match dopant configuration
  - No violations of conservation laws or symmetry

Score 12-16: Minor inconsistencies
  - Band gap magnitude off by <0.5 eV
  - Carrier concentration estimates imprecise
  - Qualitative trends correct but quantitative values approximate

Score 6-11: Significant inconsistencies
  - Wrong carrier type (n vs p)
  - Mechanical properties inconsistent with defects
  - Optical absorption doesn't match band structure

Score 0-5: Major violations
  - Metallic predicted for insulating structure
  - Physically impossible property values
  - Contradictions between different properties
""",
    },
    "causal_psp_reasoning": {
        "name": "Causal PSP Reasoning",
        "max_score": 10,
        "description": "Quality of Processing->Structure->Property causal chain",
        "rubric": """
Score 8-10: Excellent causal reasoning
  - Clear P->S->P chain with explicit connections
  - Mechanistic explanations (how processing creates structure)
  - Physical justifications grounded in theory
  - Uncertainty acknowledged and quantified
  - References to principles or literature

Score 5-7: Good partial reasoning
  - P->S->P chain present but incomplete
  - Some mechanistic explanations
  - Basic physical reasoning
  - Limited uncertainty discussion

Score 2-4: Minimal reasoning
  - Mentions connections but lacks detail
  - Empirical correlations without mechanisms
  - Weak causal links

Score 0-1: No causal reasoning
  - No P->S->P chain
  - Pure correlation or guessing
  - Missing scientific justification
""",
    },
}


# ---------------------------------------------------------------------------
# Backend abstraction
# ---------------------------------------------------------------------------

class _OllamaBackend:
    """Thin wrapper around an Ollama client for JSON generation."""

    def __init__(self, model: str = "qwen2:7b", **kwargs):
        self.model = model
        self.kwargs = kwargs
        try:
            from ollama_client import get_ollama_client  # type: ignore[import-untyped]
            self._client = get_ollama_client(model=model)
        except ImportError:
            self._client = None

    def generate_json(self, prompt: str, temperature: float = 0.0) -> dict:
        if self._client is None:
            raise RuntimeError(
                "ollama_client is not installed.  Install it or use a "
                "different backend for LLMJudge."
            )
        return self._client.generate_json(prompt, temperature=temperature)


class _OpenAIBackend:
    """Backend using the OpenAI-compatible chat completion API."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        self.model = model
        self.kwargs = kwargs
        try:
            import openai  # type: ignore[import-untyped]
            self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            raise ImportError("openai package is required for the OpenAI backend")

    def generate_json(self, prompt: str, temperature: float = 0.0) -> dict:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
        return json.loads(text)


# ---------------------------------------------------------------------------
# LLMJudge
# ---------------------------------------------------------------------------

class LLMJudge:
    """LLM-based evaluator for 2D materials processing predictions.

    Supports multiple backends (Ollama, OpenAI-compatible APIs) and scores
    predictions on four domain-specific metrics.

    Parameters
    ----------
    backend :
        ``"ollama"`` or ``"openai"``.
    model :
        Model identifier (e.g. ``"qwen2:7b"``, ``"gpt-4o-mini"``).
    temperature :
        Sampling temperature for the LLM (0 for deterministic).
    api_key :
        Optional API key (required for OpenAI backend).
    base_url :
        Optional base URL override (for custom OpenAI-compatible servers).
    """

    def __init__(
        self,
        backend: str = "ollama",
        model: str = "qwen2:7b",
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.backend_name = backend
        self.model = model
        self.temperature = temperature

        if backend == "ollama":
            self._backend = _OllamaBackend(model=model)
        elif backend == "openai":
            self._backend = _OpenAIBackend(model=model, api_key=api_key, base_url=base_url)
        else:
            raise ValueError(f"Unknown backend: {backend!r}.  Choose 'ollama' or 'openai'.")

        logger.info("LLMJudge initialised: backend=%s, model=%s", backend, model)

    # -- prompt construction ------------------------------------------------

    @staticmethod
    def _create_prompt(
        query: Dict[str, Any],
        prediction: Dict[str, Any],
        ground_truth: Dict[str, Any],
        metric_key: str,
    ) -> str:
        """Build the judge prompt for a single metric."""
        metric = METRICS[metric_key]

        return f"""You are an expert materials scientist evaluating AI-generated predictions for 2D materials processing.

**TASK:** Score the prediction on **{metric['name']}** ({metric['description']}).

**METRIC DEFINITION:**
{metric['name']} (0-{metric['max_score']} points)
{metric['description']}

**SCORING RUBRIC:**
{metric['rubric']}

---

**INPUT QUERY:**
```json
{json.dumps(query, indent=2)}
```

**GROUND TRUTH (Reference):**
```json
{json.dumps(ground_truth, indent=2)}
```

**MODEL PREDICTION (To Evaluate):**
```json
{json.dumps(prediction, indent=2)}
```

---

**EVALUATION INSTRUCTIONS:**

1. **Compare** the prediction to ground truth on {metric['name']}
2. **Score** the prediction (0-{metric['max_score']}) using the rubric above
3. **Justify** your score with specific examples from the prediction
4. **Identify** failure modes (what went wrong, if anything)
5. **Identify** strengths (what the model did well)

**OUTPUT FORMAT (strict JSON):**
```json
{{
  "metric": "{metric_key}",
  "score": <float 0-{metric['max_score']}>,
  "justification": "<detailed explanation of score>",
  "failure_modes": ["<specific issue 1>", "<specific issue 2>", ...],
  "strengths": ["<what worked well 1>", "<what worked well 2>", ...],
  "key_evidence": "<most important evidence for this score>"
}}
```

**IMPORTANT:**
- Be strict but fair - only high scores for truly excellent predictions
- Focus on {metric['name']} specifically, not overall quality
- Provide concrete evidence from the prediction text
- Output ONLY valid JSON, no other text
"""

    # -- single-metric scoring ----------------------------------------------

    def score_prediction(
        self,
        query: Dict[str, Any],
        prediction: Dict[str, Any],
        ground_truth: Dict[str, Any],
        metric_key: str,
    ) -> Dict[str, Any]:
        """Score a single prediction on a specific metric.

        Parameters
        ----------
        query :
            Input query / processing conditions.
        prediction :
            Model's prediction output.
        ground_truth :
            Reference answer.
        metric_key :
            One of ``"processing_feasibility"``, ``"structure_emergence"``,
            ``"property_consistency"``, ``"causal_psp_reasoning"``.

        Returns
        -------
        dict
            Keys: ``metric``, ``score``, ``justification``,
            ``failure_modes``, ``strengths``, ``key_evidence``.
        """
        if metric_key not in METRICS:
            raise ValueError(
                f"Unknown metric: {metric_key!r}. "
                f"Available: {list(METRICS.keys())}"
            )

        prompt = self._create_prompt(query, prediction, ground_truth, metric_key)

        try:
            response = self._backend.generate_json(prompt, temperature=self.temperature)

            required_fields = ["metric", "score", "justification", "failure_modes", "strengths"]
            for field in required_fields:
                if field not in response:
                    logger.warning("Missing field '%s' in judge response", field)
                    response[field] = [] if field.endswith("s") else ""

            max_score = METRICS[metric_key]["max_score"]
            score = response.get("score", 0)
            if not (0 <= score <= max_score):
                logger.warning(
                    "Score %s out of range [0, %d], clipping", score, max_score
                )
                response["score"] = max(0, min(score, max_score))

            return response

        except Exception as exc:
            logger.error("Judge scoring failed for %s: %s", metric_key, exc)
            return {
                "metric": metric_key,
                "score": 0.0,
                "justification": f"Evaluation failed: {exc}",
                "failure_modes": ["Judge evaluation error"],
                "strengths": [],
                "key_evidence": "",
                "error": str(exc),
            }

    # -- all-metrics evaluation ---------------------------------------------

    def evaluate_all_metrics(
        self,
        query: Dict[str, Any],
        prediction: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate a prediction on all four metrics.

        Returns a dict with ``metric_scores``, ``overall_score`` (0--100),
        and ``overall_score_normalized`` (0--100 percentage).
        """
        results: Dict[str, Any] = {
            "query": query,
            "prediction": prediction,
            "ground_truth": ground_truth,
            "metric_scores": {},
        }

        total_score = 0.0
        max_total = 100.0  # 40 + 30 + 20 + 10

        for metric_key in METRICS:
            logger.info("  Evaluating %s...", METRICS[metric_key]["name"])
            score_result = self.score_prediction(query, prediction, ground_truth, metric_key)
            results["metric_scores"][metric_key] = score_result
            total_score += score_result.get("score", 0)
            logger.info(
                "    Score: %s/%d",
                score_result.get("score", 0),
                METRICS[metric_key]["max_score"],
            )

        results["overall_score"] = total_score
        results["overall_score_normalized"] = (total_score / max_total) * 100
        return results

    # -- batch evaluation ---------------------------------------------------

    def batch_evaluate(
        self,
        test_cases: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Evaluate multiple test cases.

        Each element of *test_cases* must contain ``query``,
        ``prediction``, and ``ground_truth`` keys (and optionally ``id``).
        """
        results = []
        for i, tc in enumerate(test_cases):
            logger.info("Evaluating test case %d/%d", i + 1, len(test_cases))
            result = self.evaluate_all_metrics(
                tc.get("query", {}),
                tc.get("prediction", {}),
                tc.get("ground_truth", {}),
            )
            result["test_case_id"] = tc.get("id", i)
            results.append(result)
        return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def create_judge_report(
    evaluation_results: List[Dict[str, Any]],
    output_file: str,
) -> dict:
    """Create a human-readable evaluation report and return a summary dict.

    Parameters
    ----------
    evaluation_results :
        Output of :meth:`LLMJudge.batch_evaluate` or
        :meth:`LLMJudge.evaluate_all_metrics`.
    output_file :
        Path to write the text report.

    Returns
    -------
    dict
        Summary statistics keyed by metric name.
    """
    lines: List[str] = []
    sep = "=" * 80
    lines.append(sep)
    lines.append("ARIA: LLM Judge Evaluation Report")
    lines.append(sep)

    for i, result in enumerate(evaluation_results):
        lines.append("")
        lines.append(sep)
        lines.append(f"Test Case {i + 1}: {result.get('test_case_id', 'N/A')}")
        lines.append(sep)
        lines.append(
            f"Overall Score: {result['overall_score']:.1f}/100 "
            f"({result['overall_score_normalized']:.1f}%)"
        )
        lines.append("")

        for metric_key, score_data in result.get("metric_scores", {}).items():
            metric_name = METRICS[metric_key]["name"]
            max_score = METRICS[metric_key]["max_score"]
            lines.append(f"--- {metric_name} ---")
            lines.append(f"Score: {score_data.get('score', 0)}/{max_score}")
            lines.append(f"Justification: {score_data.get('justification', 'N/A')}")
            if score_data.get("strengths"):
                lines.append("Strengths:")
                for s in score_data["strengths"]:
                    lines.append(f"  + {s}")
            if score_data.get("failure_modes"):
                lines.append("Failure Modes:")
                for f in score_data["failure_modes"]:
                    lines.append(f"  - {f}")
            lines.append("")

    # Summary
    lines.append(sep)
    lines.append("SUMMARY STATISTICS")
    lines.append(sep)

    summary: Dict[str, Any] = {}
    if evaluation_results:
        avg_overall = sum(r["overall_score"] for r in evaluation_results) / len(
            evaluation_results
        )
        lines.append(f"Average Overall Score: {avg_overall:.1f}/100")
        lines.append("")

        for metric_key in METRICS:
            scores = [
                r["metric_scores"][metric_key]["score"] for r in evaluation_results
            ]
            avg_score = sum(scores) / len(scores)
            max_score = METRICS[metric_key]["max_score"]
            metric_name = METRICS[metric_key]["name"]
            lines.append(
                f"{metric_name}: {avg_score:.1f}/{max_score} "
                f"({(avg_score / max_score) * 100:.1f}%)"
            )
            summary[metric_key] = {
                "mean": avg_score,
                "max": max_score,
                "pct": (avg_score / max_score) * 100,
            }

    summary["overall_mean"] = avg_overall

    # Write report
    with open(output_file, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    logger.info("Judge report saved to %s", output_file)
    return summary