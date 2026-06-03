"""
ARIA Engine -- unified entry point for all operating modes.

The :class:`ARIAEngine` class consolidates the five ARIA variants
(baseline, naive_kg, aria, aria_search, aria_full) behind a single
``mode`` parameter.  All modes return the same
:class:`~aria.types.ARIAResult` data structure for consistent
comparison and evaluation.

Usage::

    from aria import ARIAEngine, load_kg

    kg = load_kg("data/aria_2d_kg_tiny.json")
    engine = ARIAEngine(kg=kg, model="qwen2:7b", mode="aria")

    # Forward prediction
    result = engine.forward_predict(
        material="MoS2",
        processing={"temperature": "750C", "method": "CVD"},
        target_property="carrier mobility",
    )
    print(result.answer, result.tier, result.confidence)

    # Inverse design
    result = engine.inverse_design(
        target_material="MoS2",
        target_property="high n-type mobility",
        constraints={"method": "CVD"},
    )

Author: ARIA Team
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import networkx as nx

from aria.types import ARIAResult, EngineMode, ReasoningTier
from aria.kg.graph_store import load_kg, kg_stats
from aria.retrieval.similarity import NodeMatcher
from aria.retrieval.path_search import find_psp_paths, extract_mechanisms
from aria.reasoning.prompts import (
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

logger = logging.getLogger(__name__)


class ARIAEngine:
    """Unified ARIA reasoning engine.

    Parameters
    ----------
    kg : nx.DiGraph or None
        Pre-loaded knowledge graph.  If *None*, *kg_file* must be provided.
    kg_file : str or None
        Path to a KG JSON file (used when *kg* is None).
    model : str
        LLM model name (e.g. ``"qwen2:7b"`` or ``"deepseek-r1:8b"``).
    mode : str
        Operating mode.  One of ``"baseline"``, ``"naive_kg"``,
        ``"aria"``, ``"aria_search"``, ``"aria_full"``.
        See :class:`~aria.types.EngineMode`.
    similarity_threshold : float
        Minimum cosine similarity for Tier 2 analogical transfer.
    embedding_model : str
        Sentence-transformer model for node embeddings.
    llm_backend : str
        LLM backend type.  Currently ``"ollama"`` is supported;
        ``"openai"`` is planned.
    llm_base_url : str
        Base URL for the LLM API.
    search_email : str
        Email for the OpenAlex polite pool.

    Raises
    ------
    ValueError
        If neither *kg* nor *kg_file* is provided in a mode that
        requires a KG.
    """

    def __init__(
        self,
        kg: Optional[nx.DiGraph] = None,
        kg_file: Optional[str] = None,
        model: str = "qwen2:7b",
        mode: str = "aria",
        similarity_threshold: float = 0.5,
        embedding_model: str = "all-MiniLM-L6-v2",
        llm_backend: str = "ollama",
        llm_base_url: str = "http://localhost:11434",
        search_email: str = "research@example.com",
    ) -> None:
        self.mode = EngineMode(mode)
        self.model = model
        self.similarity_threshold = similarity_threshold

        # ---- Load / validate KG ------------------------------------------------
        if kg is not None:
            self.kg = kg
        elif kg_file is not None:
            self.kg = load_kg(kg_file)
        elif self.mode == EngineMode.BASELINE:
            self.kg = None  # baseline does not need a KG
        else:
            raise ValueError(
                f"Mode {self.mode.value!r} requires a knowledge graph. "
                "Pass `kg` or `kg_file`."
            )

        # ---- LLM client -------------------------------------------------------
        self.llm = self._create_llm_client(llm_backend, model, llm_base_url)

        # ---- Embedding matcher (modes that need KG) ----------------------------
        self.matcher: Optional[NodeMatcher] = None
        if self.kg is not None:
            self.matcher = NodeMatcher(self.kg, model_name=embedding_model)
            self.matcher.precompute()

        # ---- Reasoners ---------------------------------------------------------
        self.tier1 = Tier1DirectReasoner(self.llm)
        self.tier2 = Tier2AnalogicalReasoner(self.llm)
        self.tier3 = Tier3FallbackReasoner(self.llm, mode=self.mode.value)
        self.router = ReasoningRouter(
            similarity_threshold=similarity_threshold
        )

        # ---- Literature searcher (aria_search / aria_full only) ----------------
        self.searcher: Optional[LiteratureSearcher] = None
        if self.mode in (EngineMode.ARIA_SEARCH, EngineMode.ARIA_FULL):
            self.searcher = LiteratureSearcher(email=search_email)

        logger.info(
            "ARIAEngine initialised: mode=%s, model=%s, kg_nodes=%s",
            self.mode.value,
            model,
            self.kg.number_of_nodes() if self.kg else "N/A",
        )

    # ------------------------------------------------------------------
    # LLM client factory
    # ------------------------------------------------------------------

    def _create_llm_client(self, backend: str, model: str, base_url: str):
        """Create an LLM client based on the backend type.

        Currently supports ``"ollama"``.  The returned object must expose
        ``generate_json(prompt, temperature) -> dict`` and
        ``generate(prompt, temperature) -> str``.
        """
        if backend == "ollama":
            from aria.llm.client import OllamaClient
            return OllamaClient(model=model, base_url=base_url)
        # Placeholder for future backends
        raise ValueError(f"Unsupported LLM backend: {backend!r}")

    # ==================================================================
    # Public API
    # ==================================================================

    def forward_predict(
        self,
        material: str = "",
        processing: Optional[Dict[str, Any]] = None,
        target_property: str = "",
        synthesis_inputs: Optional[Dict[str, Any]] = None,
    ) -> ARIAResult:
        """Predict material properties from synthesis conditions.

        Parameters
        ----------
        material : str
            Host material name (e.g. ``"MoS2"``).
        processing : dict, optional
            Processing / synthesis parameters.
        target_property : str
            Target property to focus on (used as a hint for routing).
        synthesis_inputs : dict, optional
            Full synthesis-inputs dict.  If provided, overrides
            *material* and *processing*.

        Returns
        -------
        ARIAResult
        """
        t0 = time.time()

        # Merge into a single synthesis dict
        if synthesis_inputs is None:
            synthesis_inputs = dict(processing or {})
            if material:
                synthesis_inputs["material"] = material

        # Dispatch by mode
        if self.mode == EngineMode.BASELINE:
            raw = self.tier3.forward(synthesis_inputs)
        elif self.mode == EngineMode.NAIVE_KG:
            raw = self._naive_kg_forward(synthesis_inputs)
        elif self.mode == EngineMode.ARIA:
            raw = self._aria_forward(synthesis_inputs)
        elif self.mode == EngineMode.ARIA_SEARCH:
            raw = self._aria_search_forward(synthesis_inputs)
        elif self.mode == EngineMode.ARIA_FULL:
            raw = self._aria_full_forward(synthesis_inputs)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

        elapsed_ms = (time.time() - t0) * 1000
        result = self._to_aria_result(raw, direction="forward", elapsed_ms=elapsed_ms)
        return result

    def inverse_design(
        self,
        target_material: str = "",
        target_property: str = "",
        constraints: Optional[Dict[str, Any]] = None,
        desired_properties: Optional[Dict[str, Any]] = None,
    ) -> ARIAResult:
        """Design synthesis conditions to achieve desired properties.

        Parameters
        ----------
        target_material : str
            Target material name.
        target_property : str
            Target property description.
        constraints : dict, optional
            Constraints on the synthesis design.
        desired_properties : dict, optional
            Full desired-properties dict.  If provided, overrides
            *target_material*, *target_property*, and *constraints*.

        Returns
        -------
        ARIAResult
        """
        t0 = time.time()

        if desired_properties is None:
            desired_properties = dict(constraints or {})
            if target_material:
                desired_properties["material"] = target_material
            if target_property:
                desired_properties["target_property"] = target_property

        # Dispatch by mode
        if self.mode == EngineMode.BASELINE:
            raw = self.tier3.inverse(desired_properties)
        elif self.mode == EngineMode.NAIVE_KG:
            raw = self._naive_kg_inverse(desired_properties)
        elif self.mode == EngineMode.ARIA:
            raw = self._aria_inverse(desired_properties)
        elif self.mode == EngineMode.ARIA_SEARCH:
            raw = self._aria_search_inverse(desired_properties)
        elif self.mode == EngineMode.ARIA_FULL:
            raw = self._aria_full_inverse(desired_properties)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

        elapsed_ms = (time.time() - t0) * 1000
        result = self._to_aria_result(raw, direction="inverse", elapsed_ms=elapsed_ms)
        return result

    def diagnose_kg(self) -> Dict[str, Any]:
        """Return diagnostic statistics about the loaded KG.

        Returns
        -------
        dict
            Stats dict (node count, edge count, root/leaf nodes, etc.)
            or a message if no KG is loaded.
        """
        if self.kg is None:
            return {"status": "No KG loaded", "mode": self.mode.value}
        return kg_stats(self.kg)

    # ==================================================================
    # Mode-specific implementations
    # ==================================================================

    # ---- NAIVE_KG ----------------------------------------------------

    def _naive_kg_forward(self, synthesis_inputs: Dict[str, Any]) -> Dict:
        """Forward prediction using simple KG concatenation (no tiers)."""
        input_keywords = self._extract_keywords(synthesis_inputs)
        property_keywords = ["mobility", "conductivity", "carrier", "band gap", "property"]

        paths = find_psp_paths(self.kg, input_keywords, property_keywords)
        mechanisms_raw = extract_mechanisms(self.kg, paths)
        # Format for the naive prompt
        formatted_mechs = "\n".join(
            f"  Path {i+1}: {' -> '.join(p)}"
            for i, p in enumerate(paths)
        ) if paths else "No relevant causal pathways found in the knowledge graph."

        prompt = NAIVE_KG_FORWARD_PROMPT.format(
            kg_context=formatted_mechs,
            synthesis_inputs=json.dumps(synthesis_inputs, indent=2),
            num_paths=len(paths),
        )
        try:
            response = self.llm.generate_json(prompt, temperature=0.0)
            response["kg_paths_used"] = len(paths)
            if "reasoning_type" not in response:
                response["reasoning_type"] = "naive_kg"
            return response
        except Exception as exc:
            logger.error("Naive KG forward failed: %s", exc)
            return {
                "predicted_properties": {},
                "mechanistic_explanation": f"Error: {exc}",
                "confidence": 0.0,
                "kg_paths_used": len(paths),
                "reasoning_type": "naive_kg_error",
            }

    def _naive_kg_inverse(self, desired_properties: Dict[str, Any]) -> Dict:
        """Inverse design using simple KG concatenation (no tiers)."""
        property_keywords = self._extract_keywords(desired_properties)
        synthesis_keywords = ["temperature", "pressure", "time", "atmosphere", "method", "CVD", "MBE"]

        paths = find_psp_paths(self.kg, property_keywords, synthesis_keywords)
        fwd_paths = find_psp_paths(self.kg, synthesis_keywords, property_keywords)
        all_paths = paths + fwd_paths
        mechanisms_raw = extract_mechanisms(self.kg, all_paths)

        formatted_mechs = "\n".join(
            f"  Path {i+1}: {' -> '.join(p)}"
            for i, p in enumerate(all_paths)
        ) if all_paths else "No relevant causal pathways found in the knowledge graph."

        prompt = NAIVE_KG_INVERSE_PROMPT.format(
            kg_context=formatted_mechs,
            desired_properties=json.dumps(desired_properties, indent=2),
            num_paths=len(all_paths),
        )
        try:
            response = self.llm.generate_json(prompt, temperature=0.0)
            response["kg_paths_used"] = len(all_paths)
            if "reasoning_type" not in response:
                response["reasoning_type"] = "naive_kg_inverse"
            return response
        except Exception as exc:
            logger.error("Naive KG inverse failed: %s", exc)
            return {
                "suggested_synthesis_conditions": {},
                "mechanistic_explanation": f"Error: {exc}",
                "confidence": 0.0,
                "kg_paths_used": len(all_paths),
                "reasoning_type": "naive_kg_inverse_error",
            }

    # ---- ARIA (3-tier cascade) ---------------------------------------

    def _aria_forward(self, synthesis_inputs: Dict[str, Any]) -> Dict:
        """Forward prediction with 3-tier causal reasoning."""
        decision = self.router.route_forward(
            synthesis_inputs, self.kg, self.matcher
        )

        if decision.tier == ReasoningTier.DIRECT:
            return self.tier1.forward(
                self.kg, synthesis_inputs,
                decision.paths, decision.mechanisms,
            )
        elif decision.tier == ReasoningTier.ANALOGICAL:
            return self.tier2.forward(
                self.kg, synthesis_inputs,
                decision.paths, decision.mechanisms,
                similar_node=decision.similar_node,
                similarity=decision.similarity,
            )
        else:
            return self.tier3.forward(synthesis_inputs)

    def _aria_inverse(self, desired_properties: Dict[str, Any]) -> Dict:
        """Inverse design with 3-tier causal reasoning."""
        decision = self.router.route_inverse(
            desired_properties, self.kg, self.matcher
        )

        if decision.tier == ReasoningTier.DIRECT:
            return self.tier1.inverse(
                self.kg, desired_properties,
                decision.paths, decision.mechanisms,
            )
        elif decision.tier == ReasoningTier.ANALOGICAL:
            return self.tier2.inverse(
                self.kg, desired_properties,
                decision.paths, decision.mechanisms,
                similar_node=decision.similar_node,
                similarity=decision.similarity,
                embedding_distance=decision.embedding_distance,
            )
        else:
            return self.tier3.inverse(desired_properties)

    # ---- ARIA_SEARCH (3-tier + literature search) -----------------------

    def _aria_search_forward(self, synthesis_inputs: Dict[str, Any]) -> Dict:
        """Forward prediction with 3-tier reasoning + literature search."""
        # Route
        decision = self.router.route_forward(
            synthesis_inputs, self.kg, self.matcher
        )

        # Perform literature search
        input_keywords = self._extract_keywords(synthesis_inputs)
        search_queries = self._build_search_queries(synthesis_inputs, decision.paths, "forward")
        lit_results = self._search_literature(search_queries)
        lit_context = self._format_literature_context(lit_results)

        if decision.tier == ReasoningTier.DIRECT:
            result = self.tier1.forward(
                self.kg, synthesis_inputs,
                decision.paths, decision.mechanisms,
            )
        elif decision.tier == ReasoningTier.ANALOGICAL:
            result = self.tier2.forward(
                self.kg, synthesis_inputs,
                decision.paths, decision.mechanisms,
                similar_node=decision.similar_node,
                similarity=decision.similarity,
            )
        else:
            result = self.tier3.forward(synthesis_inputs)

        # Enrich result with literature metadata
        result["literature_papers"] = lit_results
        result["literature_context"] = lit_context
        return result

    def _aria_search_inverse(self, desired_properties: Dict[str, Any]) -> Dict:
        """Inverse design with 3-tier reasoning + literature search."""
        decision = self.router.route_inverse(
            desired_properties, self.kg, self.matcher
        )

        search_queries = self._build_search_queries(desired_properties, decision.paths, "inverse")
        lit_results = self._search_literature(search_queries)
        lit_context = self._format_literature_context(lit_results)

        if decision.tier == ReasoningTier.DIRECT:
            result = self.tier1.inverse(
                self.kg, desired_properties,
                decision.paths, decision.mechanisms,
            )
        elif decision.tier == ReasoningTier.ANALOGICAL:
            result = self.tier2.inverse(
                self.kg, desired_properties,
                decision.paths, decision.mechanisms,
                similar_node=decision.similar_node,
                similarity=decision.similarity,
                embedding_distance=decision.embedding_distance,
            )
        else:
            result = self.tier3.inverse(desired_properties)

        result["literature_papers"] = lit_results
        result["literature_context"] = lit_context
        return result

    # ---- ARIA_FULL (3-tier + literature + CoT) -------------------------

    def _aria_full_forward(self, synthesis_inputs: Dict[str, Any]) -> Dict:
        """Forward prediction with 3-tier reasoning + literature + CoT."""
        # Route
        decision = self.router.route_forward(
            synthesis_inputs, self.kg, self.matcher
        )

        # Literature search
        search_queries = self._build_search_queries(synthesis_inputs, decision.paths, "forward")
        lit_results = self._search_literature(search_queries)
        lit_context = self._format_literature_context(lit_results)

        # Get tier result
        if decision.tier == ReasoningTier.DIRECT:
            tier_result = self.tier1.forward(
                self.kg, synthesis_inputs,
                decision.paths, decision.mechanisms,
            )
        elif decision.tier == ReasoningTier.ANALOGICAL:
            tier_result = self.tier2.forward(
                self.kg, synthesis_inputs,
                decision.paths, decision.mechanisms,
                similar_node=decision.similar_node,
                similarity=decision.similarity,
            )
        else:
            tier_result = self.tier3.forward(synthesis_inputs)

        # Build chain-of-thought
        from aria.types import ChainOfThought, KnowledgeSource, ReasoningStep

        kg_sources = self._extract_kg_sources(decision.paths)
        lit_sources = [
            KnowledgeSource(
                source_id=f"lit_{i}",
                content=p.get("title", "Untitled"),
                source_type="literature",
                confidence=min(1.0, 0.5 + p.get("citations", 0) / 1000),
                context=f"{p.get('year', 'N/A')} ({p.get('citations', 0)} citations)",
                metadata=p,
            )
            for i, p in enumerate(lit_results)
        ]

        steps = [
            ReasoningStep(
                step_id="kg_retrieval",
                description=f"Found {len(decision.paths)} paths at tier {decision.tier.value}",
                evidence_sources=kg_sources[:5],
                reasoning_type="retrieval",
                confidence=1.0 if decision.paths else 0.0,
                intermediate_conclusion=f"Tier {decision.tier.value} selected",
            ),
            ReasoningStep(
                step_id="literature_search",
                description=f"Retrieved {len(lit_results)} papers",
                evidence_sources=lit_sources[:5],
                reasoning_type="search",
                confidence=0.8 if lit_results else 0.3,
                intermediate_conclusion=f"{len(lit_results)} relevant papers found",
            ),
            ReasoningStep(
                step_id="llm_synthesis",
                description=f"Generated prediction via Tier {decision.tier.value}",
                evidence_sources=[],
                reasoning_type="synthesis",
                confidence=tier_result.get("confidence", 0.5),
                intermediate_conclusion=tier_result.get("reasoning", "")[:200],
            ),
        ]

        cot = ChainOfThought(
            query_context={"type": "forward", "inputs": synthesis_inputs},
            reasoning_steps=steps,
            final_reasoning=tier_result.get("reasoning", ""),
            final_result=tier_result.get("predicted_properties", {}),
            confidence_breakdown={s.step_id: s.confidence for s in steps},
            source_attribution={
                "kg_sources": len(kg_sources),
                "literature_sources": len(lit_sources),
                "total_sources": len(kg_sources) + len(lit_sources),
            },
            tier=decision.tier.value,
            kg_paths_used=len(decision.paths),
            literature_papers_used=len(lit_results),
        )

        tier_result["chain_of_thought"] = cot.to_dict()
        tier_result["literature_papers"] = lit_results
        tier_result["literature_context"] = lit_context
        return tier_result

    def _aria_full_inverse(self, desired_properties: Dict[str, Any]) -> Dict:
        """Inverse design with 3-tier reasoning + literature + CoT."""
        decision = self.router.route_inverse(
            desired_properties, self.kg, self.matcher
        )

        search_queries = self._build_search_queries(desired_properties, decision.paths, "inverse")
        lit_results = self._search_literature(search_queries)
        lit_context = self._format_literature_context(lit_results)

        if decision.tier == ReasoningTier.DIRECT:
            tier_result = self.tier1.inverse(
                self.kg, desired_properties,
                decision.paths, decision.mechanisms,
            )
        elif decision.tier == ReasoningTier.ANALOGICAL:
            tier_result = self.tier2.inverse(
                self.kg, desired_properties,
                decision.paths, decision.mechanisms,
                similar_node=decision.similar_node,
                similarity=decision.similarity,
                embedding_distance=decision.embedding_distance,
            )
        else:
            tier_result = self.tier3.inverse(desired_properties)

        from aria.types import ChainOfThought, KnowledgeSource, ReasoningStep

        kg_sources = self._extract_kg_sources(decision.paths)
        lit_sources = [
            KnowledgeSource(
                source_id=f"lit_{i}",
                content=p.get("title", "Untitled"),
                source_type="literature",
                confidence=min(1.0, 0.5 + p.get("citations", 0) / 1000),
                context=f"{p.get('year', 'N/A')} ({p.get('citations', 0)} citations)",
                metadata=p,
            )
            for i, p in enumerate(lit_results)
        ]

        steps = [
            ReasoningStep(
                step_id="kg_retrieval_inverse",
                description=f"Found {len(decision.paths)} inverse paths at tier {decision.tier.value}",
                evidence_sources=kg_sources[:5],
                reasoning_type="retrieval",
                confidence=1.0 if decision.paths else 0.0,
                intermediate_conclusion=f"Tier {decision.tier.value} selected (inverse)",
            ),
            ReasoningStep(
                step_id="literature_search_inverse",
                description=f"Retrieved {len(lit_results)} papers",
                evidence_sources=lit_sources[:5],
                reasoning_type="search",
                confidence=0.8 if lit_results else 0.3,
                intermediate_conclusion=f"{len(lit_results)} papers with relevant synthesis protocols",
            ),
            ReasoningStep(
                step_id="llm_synthesis_inverse",
                description=f"Generated synthesis conditions via Tier {decision.tier.value}",
                evidence_sources=[],
                reasoning_type="synthesis",
                confidence=tier_result.get("confidence", 0.5),
                intermediate_conclusion=tier_result.get("reasoning", "")[:200],
            ),
        ]

        cot = ChainOfThought(
            query_context={"type": "inverse", "properties": desired_properties},
            reasoning_steps=steps,
            final_reasoning=tier_result.get("reasoning", ""),
            final_result=tier_result.get("suggested_synthesis_conditions", {}),
            confidence_breakdown={s.step_id: s.confidence for s in steps},
            source_attribution={
                "kg_sources": len(kg_sources),
                "literature_sources": len(lit_sources),
                "total_sources": len(kg_sources) + len(lit_sources),
            },
            tier=decision.tier.value,
            kg_paths_used=len(decision.paths),
            literature_papers_used=len(lit_results),
        )

        tier_result["chain_of_thought"] = cot.to_dict()
        tier_result["literature_papers"] = lit_results
        tier_result["literature_context"] = lit_context
        return tier_result

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _to_aria_result(
        self,
        raw: Dict[str, Any],
        direction: str,
        elapsed_ms: float,
    ) -> ARIAResult:
        """Convert a raw dict from any mode into a unified ARIAResult."""
        tier_val = raw.get("tier", 3)
        if isinstance(tier_val, ReasoningTier):
            tier = tier_val
        else:
            tier = ReasoningTier(int(tier_val))

        answer = raw.get("predicted_properties") or raw.get("suggested_synthesis_conditions", {})

        # Extract paths
        kg_paths = raw.get("kg_paths", [])
        if isinstance(kg_paths, int):
            kg_paths_used = kg_paths
            kg_paths = raw.get("paths", [])
        else:
            kg_paths_used = len(kg_paths) if isinstance(kg_paths, list) else 0

        # Literature
        lit_papers = raw.get("literature_papers", [])

        # Causal trace (best-effort extraction)
        from aria.types import CausalTraceStep
        causal_trace = []
        mech = raw.get("mechanistic_explanation", {})
        if isinstance(mech, str):
            try:
                mech = json.loads(mech)
            except (json.JSONDecodeError, TypeError):
                mech = {}
        if isinstance(mech, dict):
            cot_steps = mech.get("chain_of_thought", [])
            for step_text in cot_steps:
                causal_trace.append(
                    CausalTraceStep(
                        processing="",
                        structure="",
                        property_="",
                        evidence_text=str(step_text),
                        confidence=0.8,
                    )
                )

        # Chain of thought
        cot_raw = raw.get("chain_of_thought")
        chain_of_thought = None
        if cot_raw is not None:
            if isinstance(cot_raw, dict):
                from aria.types import ChainOfThought as CoT
                try:
                    chain_of_thought = CoT(**cot_raw)
                except Exception:
                    pass

        return ARIAResult(
            answer=answer,
            tier=tier,
            confidence=float(raw.get("confidence", 0.0)),
            reasoning_type=raw.get("reasoning_type", "unknown"),
            causal_trace=causal_trace,
            missing_evidence=raw.get("missing_evidence", []),
            kg_paths_used=kg_paths_used,
            kg_paths=kg_paths if isinstance(kg_paths, list) else [],
            literature_papers=lit_papers,
            source_attribution=raw.get("source_attribution", {}),
            chain_of_thought=chain_of_thought,
            mode=self.mode.value,
            model=self.model,
            latency_ms=elapsed_ms,
        )

    @staticmethod
    def _extract_keywords(data: Dict[str, Any]) -> List[str]:
        """Extract search keywords from a dict of inputs."""
        keywords: list[str] = []
        for value in data.values():
            if value is not None:
                keywords.append(str(value))
        return keywords

    def _build_search_queries(
        self,
        prompt_data: Dict,
        paths: List[str],
        query_type: str,
    ) -> List[str]:
        """Generate targeted literature search queries."""
        key_terms = [str(v) for v in prompt_data.values() if v][:5]
        queries = []

        # Path-based queries
        for path in paths[:3]:
            path_terms = path.replace(" -> ", " ").replace("_", " ")
            queries.append(f"experimental validation {path_terms}")
            queries.append(f"mechanism {path_terms} materials science")

        # General queries
        if query_type == "forward":
            queries.extend([
                f"quantitative data {' '.join(key_terms[:3])} experimental",
                f"recent advances {' '.join(key_terms[:3])}",
            ])
        else:
            queries.extend([
                f"synthesis methods {' '.join(key_terms[:3])}",
                f"achieving {' '.join(key_terms[:3])} materials",
            ])

        return queries[:12]

    def _search_literature(self, queries: List[str], max_papers: int = 10) -> List[Dict]:
        """Execute literature searches via LiteratureSearcher."""
        if self.searcher is None:
            return []

        all_papers: list[dict] = []
        for query in queries[:5]:
            papers = self.searcher.search(query, max_results=3, use_both=False)
            all_papers.extend(papers)

        # Deduplicate by title
        unique: dict[str, dict] = {}
        for p in all_papers:
            title_lower = p.get("title", "").lower()
            if title_lower and title_lower not in unique:
                unique[title_lower] = p

        result = list(unique.values())[:max_papers]
        result.sort(key=lambda x: x.get("citations", 0), reverse=True)
        return result

    @staticmethod
    def _format_literature_context(search_results: List[Dict]) -> str:
        """Format search results for inclusion in an LLM prompt."""
        if not search_results:
            return "No relevant literature found."

        context = f"**Literature Search Results ({len(search_results)} papers found):**\n\n"
        for i, paper in enumerate(search_results[:10], 1):
            authors = ", ".join(paper.get("authors", ["Unknown"]))
            year = paper.get("year", "N/A")
            title = paper.get("title", "Untitled")
            abstract = paper.get("abstract", "No abstract available.")
            citations = paper.get("citations", 0)

            if len(abstract) > 300:
                abstract = abstract[:300] + "..."

            context += f"{i}. **{title}** ({year})\n"
            context += f"   Authors: {authors}\n"
            context += f"   Citations: {citations}\n"
            context += f"   Abstract: {abstract}\n"
            context += f"   Source: {paper.get('source', 'Unknown')}\n\n"

        return context

    def _extract_kg_sources(self, paths: List[str]) -> list:
        """Extract KnowledgeSource objects from KG paths."""
        from aria.types import KnowledgeSource
        sources: list[KnowledgeSource] = []

        for path_str in paths[:5]:
            nodes = path_str.split(" -> ")
            for node in nodes:
                sources.append(
                    KnowledgeSource(
                        source_id=f"kg_node_{hash(node)}",
                        content=node.strip(),
                        source_type="kg_node",
                        confidence=1.0,
                        context="Knowledge graph node",
                    )
                )
            for i in range(len(nodes) - 1):
                src, tgt = nodes[i].strip(), nodes[i + 1].strip()
                if self.kg.has_edge(src, tgt):
                    mech = self.kg[src][tgt].get("mechanism", "")
                    if mech:
                        sources.append(
                            KnowledgeSource(
                                source_id=f"kg_mech_{hash(src + tgt)}",
                                content=mech,
                                source_type="kg_mechanism",
                                confidence=0.95,
                                context=f"Mechanism for {src} -> {tgt}",
                            )
                        )
        return sources