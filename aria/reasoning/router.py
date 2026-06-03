"""
Reasoning Router -- dispatches queries to the appropriate tier.

The router examines KG availability and causal completeness to decide
whether a query should go through Tier 1 (direct), Tier 2 (analogical),
or Tier 3 (fallback).

Author: ARIA Team
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from aria.types import ReasoningTier

logger = logging.getLogger(__name__)


class RoutingDecision:
    """Outcome of a routing decision.

    Attributes
    ----------
    tier : ReasoningTier
        The selected reasoning tier.
    paths : list[str]
        Causal paths found in the KG (empty for Tier 3).
    mechanisms : list[str]
        Mechanism quotes extracted from the paths.
    similar_node : str or None
        The closest KG node (only set for Tier 2).
    similarity : float
        Cosine similarity to the similar node (only for Tier 2).
    embedding_distance : float
        1 - cosine_similarity (only for Tier 2 inverse).
    """

    def __init__(
        self,
        tier: ReasoningTier,
        paths: Optional[List[str]] = None,
        mechanisms: Optional[List[str]] = None,
        similar_node: Optional[str] = None,
        similarity: float = 0.0,
        embedding_distance: float = 0.0,
    ) -> None:
        self.tier = tier
        self.paths = paths or []
        self.mechanisms = mechanisms or []
        self.similar_node = similar_node
        self.similarity = similarity
        self.embedding_distance = embedding_distance

    def to_dict(self) -> dict:
        return {
            "tier": self.tier.value,
            "paths": self.paths,
            "mechanisms": self.mechanisms,
            "similar_node": self.similar_node,
            "similarity": self.similarity,
            "embedding_distance": self.embedding_distance,
        }


class ReasoningRouter:
    """Dispatches queries to the appropriate reasoning tier.

    The routing logic is:

    1. **Tier 1 (Direct):** Try keyword-based path search in the KG.
       If paths are found, route to Tier 1.

    2. **Tier 2 (Analogical):** If no direct paths, find the most
       semantically similar KG node.  If its cosine similarity exceeds
       ``similarity_threshold``, route to Tier 2.

    3. **Tier 3 (Fallback):** If neither KG paths nor a sufficiently
       similar node is found, route to Tier 3 (pure LLM).

    Parameters
    ----------
    similarity_threshold : float
        Minimum cosine similarity to accept a Tier 2 analogy.
        Default 0.5.
    """

    def __init__(self, similarity_threshold: float = 0.5) -> None:
        self.similarity_threshold = similarity_threshold

    def route_forward(
        self,
        query: Dict[str, Any],
        graph,               # nx.DiGraph
        matcher,             # NodeMatcher from aria.retrieval.similarity
        completeness_threshold: float = 0.3,
    ) -> RoutingDecision:
        """Route a forward-prediction query.

        Parameters
        ----------
        query : dict
            Synthesis inputs, e.g. ``{"method": "CVD", "temperature_c": 750}``.
        graph : nx.DiGraph
            The knowledge graph.
        matcher : NodeMatcher
            Embedding-based matcher exposing ``find_most_similar()`` and
            ``embedding_distance()``.
        completeness_threshold : float
            Unused currently; reserved for future causal-completeness check.

        Returns
        -------
        RoutingDecision
        """
        # Extract keyword list from query values
        input_keywords = [str(v) for v in query.values() if v is not None]

        # --- Tier 1: direct path match ---
        property_nodes = [
            n for n in graph.nodes() if graph.out_degree(n) == 0
        ]
        paths = self._find_paths(graph, input_keywords, property_nodes)

        if paths:
            mechanisms = self._extract_mechanisms(graph, paths)
            logger.info(
                "Router: Tier 1 (direct) -- %d paths found", len(paths)
            )
            return RoutingDecision(
                tier=ReasoningTier.DIRECT,
                paths=paths,
                mechanisms=mechanisms,
            )

        # --- Tier 2: analogical transfer ---
        synthesis_nodes = [
            n for n in graph.nodes() if graph.in_degree(n) == 0
        ]
        query_string = " and ".join(input_keywords)
        similar_node, score = matcher.find_most_similar(
            query_string, synthesis_nodes
        )

        if similar_node and score > self.similarity_threshold:
            analogous_paths = self._find_paths(
                graph, [similar_node], property_nodes
            )
            if analogous_paths:
                mechanisms = self._extract_mechanisms(graph, analogous_paths)
                logger.info(
                    "Router: Tier 2 (analogical) -- node=%s, sim=%.3f",
                    similar_node,
                    score,
                )
                return RoutingDecision(
                    tier=ReasoningTier.ANALOGICAL,
                    paths=analogous_paths,
                    mechanisms=mechanisms,
                    similar_node=similar_node,
                    similarity=score,
                )

        # --- Tier 3: fallback ---
        logger.info("Router: Tier 3 (fallback) -- no KG evidence")
        return RoutingDecision(tier=ReasoningTier.FALLBACK)

    def route_inverse(
        self,
        query: Dict[str, Any],
        graph,
        matcher,
        completeness_threshold: float = 0.3,
    ) -> RoutingDecision:
        """Route an inverse-design query.

        Parameters
        ----------
        query : dict
            Desired properties, e.g. ``{"carrier_type": "n-type", "mobility": "high"}``.
        graph : nx.DiGraph
        matcher : NodeMatcher
        completeness_threshold : float

        Returns
        -------
        RoutingDecision
        """
        property_keywords = [str(v) for v in query.values() if v is not None]
        synthesis_nodes = [
            n for n in graph.nodes() if graph.in_degree(n) == 0
        ]

        # --- Tier 1: direct inverse path match ---
        paths = self._find_paths(
            graph, synthesis_nodes, property_keywords, reverse=True
        )

        if paths:
            mechanisms = self._extract_mechanisms(graph, paths)
            logger.info(
                "Router: Tier 1 inverse -- %d paths found", len(paths)
            )
            return RoutingDecision(
                tier=ReasoningTier.DIRECT,
                paths=paths,
                mechanisms=mechanisms,
            )

        # --- Tier 2: analogical transfer (inverse) ---
        property_nodes = [
            n for n in graph.nodes() if graph.out_degree(n) == 0
        ]
        query_string = " and ".join(property_keywords)
        similar_node, score = matcher.find_most_similar(
            query_string, property_nodes
        )

        if similar_node and score > self.similarity_threshold:
            analogous_paths = self._find_paths(
                graph, synthesis_nodes, [similar_node], reverse=True
            )
            if analogous_paths:
                mechanisms = self._extract_mechanisms(graph, analogous_paths)
                embedding_distance = matcher.embedding_distance(
                    query_string, similar_node
                )
                logger.info(
                    "Router: Tier 2 inverse -- node=%s, sim=%.3f",
                    similar_node,
                    score,
                )
                return RoutingDecision(
                    tier=ReasoningTier.ANALOGICAL,
                    paths=analogous_paths,
                    mechanisms=mechanisms,
                    similar_node=similar_node,
                    similarity=score,
                    embedding_distance=embedding_distance,
                )

        # --- Tier 3: fallback ---
        logger.info("Router: Tier 3 inverse -- no KG evidence")
        return RoutingDecision(tier=ReasoningTier.FALLBACK)

    # ------------------------------------------------------------------
    # Static helpers (path search & mechanism extraction)
    # ------------------------------------------------------------------

    @staticmethod
    def _find_paths(
        graph,
        start_keywords: List[str],
        end_keywords: List[str],
        reverse: bool = False,
        max_paths: int = 10,
        cutoff: int = 4,
    ) -> List[str]:
        """Find causal paths in the KG via keyword matching.

        Parameters
        ----------
        graph : nx.DiGraph
        start_keywords : list[str]
        end_keywords : list[str]
        reverse : bool
            If True, reverse the graph before searching (for inverse design).
        max_paths : int
        cutoff : int
            Maximum path length.

        Returns
        -------
        list[str]
            Path strings like ``"A -> B -> C"``.
        """
        import networkx as nx  # local import to avoid hard dep at module level

        start_nodes = {
            n for n in graph.nodes()
            if any(kw.lower() in n.lower() for kw in start_keywords if kw)
        }
        end_nodes = {
            n for n in graph.nodes()
            if any(kw.lower() in n.lower() for kw in end_keywords if kw)
        }

        if not start_nodes or not end_nodes:
            return []

        g = graph.reverse(copy=True) if reverse else graph
        sources = end_nodes if reverse else start_nodes
        targets = start_nodes if reverse else end_nodes

        valid_paths: list[str] = []
        for source in sources:
            for target in targets:
                if nx.has_path(g, source, target):
                    for path in nx.all_simple_paths(g, source, target, cutoff=cutoff):
                        valid_paths.append(" -> ".join(path))
                        if len(valid_paths) >= max_paths:
                            return list(set(valid_paths))[:max_paths]

        return list(set(valid_paths))[:max_paths]

    @staticmethod
    def _extract_mechanisms(graph, paths: List[str]) -> List[str]:
        """Extract mechanism quotes from edges along each path."""
        mechanisms: list[str] = []
        for path_str in paths:
            nodes = path_str.split(" -> ")
            for i in range(len(nodes) - 1):
                if graph.has_edge(nodes[i], nodes[i + 1]):
                    mech = graph[nodes[i]][nodes[i + 1]].get("mechanism", "")
                    if mech and mech.strip():
                        mechanisms.append(mech.strip())
        return mechanisms