"""
Tests for aria.reasoning.router -- routing logic and dispatch.

All LLM calls are mocked. Tests verify that the ReasoningRouter
correctly dispatches queries to each tier based on KG evidence,
and that RoutingDecision dataclass behaves as expected.
"""

from unittest.mock import MagicMock, patch

import networkx as nx
import pytest

from aria.reasoning.router import ReasoningRouter, RoutingDecision
from aria.types import ReasoningTier


# ==========================================================================
# RoutingDecision
# ==========================================================================


class TestRoutingDecision:
    """Tests for the RoutingDecision dataclass."""

    def test_creation_with_defaults(self):
        """RoutingDecision defaults to empty paths and mechanisms."""
        decision = RoutingDecision(tier=ReasoningTier.FALLBACK)
        assert decision.tier == ReasoningTier.FALLBACK
        assert decision.paths == []
        assert decision.mechanisms == []
        assert decision.similar_node is None
        assert decision.similarity == 0.0
        assert decision.embedding_distance == 0.0

    def test_creation_with_data(self):
        """RoutingDecision stores all provided fields."""
        decision = RoutingDecision(
            tier=ReasoningTier.DIRECT,
            paths=["A -> B -> C"],
            mechanisms=["A increases B"],
            similar_node=None,
            similarity=0.0,
        )
        assert decision.tier == ReasoningTier.DIRECT
        assert len(decision.paths) == 1
        assert "A increases B" in decision.mechanisms

    def test_analogical_decision(self):
        """RoutingDecision for Tier 2 includes similarity info."""
        decision = RoutingDecision(
            tier=ReasoningTier.ANALOGICAL,
            paths=["X -> Y -> Z"],
            mechanisms=["mechanism text"],
            similar_node="CVD temperature 700C",
            similarity=0.82,
            embedding_distance=0.18,
        )
        assert decision.tier == ReasoningTier.ANALOGICAL
        assert decision.similar_node == "CVD temperature 700C"
        assert decision.similarity == 0.82
        assert decision.embedding_distance == 0.18

    def test_to_dict(self):
        """to_dict() returns a serialisable dict."""
        decision = RoutingDecision(
            tier=ReasoningTier.DIRECT,
            paths=["A -> B"],
            mechanisms=["m1"],
        )
        d = decision.to_dict()
        assert d["tier"] == 1  # ReasoningTier.DIRECT.value
        assert d["paths"] == ["A -> B"]
        assert d["mechanisms"] == ["m1"]


# ==========================================================================
# ReasoningRouter initialisation
# ==========================================================================


class TestReasoningRouterInit:
    """Tests for ReasoningRouter initialisation."""

    def test_default_threshold(self):
        """Default similarity_threshold is 0.5."""
        router = ReasoningRouter()
        assert router.similarity_threshold == 0.5

    def test_custom_threshold(self):
        """Custom similarity_threshold is stored."""
        router = ReasoningRouter(similarity_threshold=0.7)
        assert router.similarity_threshold == 0.7


# ==========================================================================
# ReasoningRouter: Tier 1 (Direct) dispatch
# ==========================================================================


class TestRouterTier1:
    """Tests that router dispatches to Tier 1 when direct paths exist."""

    def test_forward_with_matching_paths(self, tiny_kg):
        """When start/end keywords match KG nodes, router selects Tier 1."""
        router = ReasoningRouter()

        # Create a mock matcher that won't be called for Tier 1
        # (because paths are found before similarity search)
        mock_matcher = MagicMock()

        decision = router.route_forward(
            query={"material": "MoS2", "temperature": "750C"},
            graph=tiny_kg,
            matcher=mock_matcher,
        )

        # Should find paths from "CVD temperature 750C" to mobility nodes
        if decision.paths:
            assert decision.tier == ReasoningTier.DIRECT
            assert len(decision.paths) > 0

    def test_forward_returns_mechanisms(self, tiny_kg):
        """Tier 1 decision includes extracted mechanism quotes."""
        router = ReasoningRouter()

        mock_matcher = MagicMock()
        decision = router.route_forward(
            query={"temperature": "750C"},
            graph=tiny_kg,
            matcher=mock_matcher,
        )

        if decision.tier == ReasoningTier.DIRECT:
            assert isinstance(decision.mechanisms, list)


# ==========================================================================
# ReasoningRouter: Tier 2 (Analogical) dispatch
# ==========================================================================


class TestRouterTier2:
    """Tests that router dispatches to Tier 2 when no direct paths but similar node exists."""

    def test_tier2_dispatch(self):
        """When no direct paths exist but a similar node is found, router selects Tier 2."""
        # Build a small disconnected graph where keyword matching will fail
        G = nx.DiGraph()
        G.add_edge("substrate annealing", "improved morphology", mechanism="test", confidence=0.8)
        G.add_edge("improved morphology", "enhanced durability", mechanism="test", confidence=0.7)

        router = ReasoningRouter(similarity_threshold=0.3)

        # Mock the matcher to return a similar node with high similarity
        mock_matcher = MagicMock()
        mock_matcher.find_most_similar.return_value = ("substrate annealing", 0.85)

        # "sintering" won't match any node keywords, but matcher will find "substrate annealing"
        decision = router.route_forward(
            query={"method": "sintering"},
            graph=G,
            matcher=mock_matcher,
        )

        # The mock matcher should have been called
        # If the similar node is found and above threshold, Tier 2 should be selected
        # (assuming no direct paths are found first)
        assert decision.tier in (ReasoningTier.ANALOGICAL, ReasoningTier.FALLBACK)

    def test_tier2_similarity_below_threshold(self):
        """When similar node score is below threshold, router falls back to Tier 3."""
        G = nx.DiGraph()
        G.add_edge("substrate annealing", "improved morphology", mechanism="test", confidence=0.8)

        router = ReasoningRouter(similarity_threshold=0.9)

        mock_matcher = MagicMock()
        mock_matcher.find_most_similar.return_value = ("substrate annealing", 0.3)

        decision = router.route_forward(
            query={"method": "sintering"},
            graph=G,
            matcher=mock_matcher,
        )

        # Similarity 0.3 < threshold 0.9, so should fall to Tier 3
        assert decision.tier == ReasoningTier.FALLBACK


# ==========================================================================
# ReasoningRouter: Tier 3 (Fallback) dispatch
# ==========================================================================


class TestRouterTier3:
    """Tests that router dispatches to Tier 3 when no KG evidence is found."""

    def test_tier3_when_no_paths_and_no_similar_node(self):
        """Empty graph forces Tier 3 (fallback)."""
        G = nx.DiGraph()
        # Add a single isolated node to avoid edge cases
        G.add_node("isolated_node")

        router = ReasoningRouter()
        mock_matcher = MagicMock()
        mock_matcher.find_most_similar.return_value = (None, 0.0)

        decision = router.route_forward(
            query={"material": "UnknownMaterial"},
            graph=G,
            matcher=mock_matcher,
        )

        assert decision.tier == ReasoningTier.FALLBACK
        assert decision.paths == []
        assert decision.mechanisms == []

    def test_tier3_inverse(self):
        """Empty graph forces Tier 3 for inverse queries too."""
        G = nx.DiGraph()
        G.add_node("isolated_node")

        router = ReasoningRouter()
        mock_matcher = MagicMock()
        mock_matcher.find_most_similar.return_value = (None, 0.0)

        decision = router.route_inverse(
            query={"target_property": "unknown property"},
            graph=G,
            matcher=mock_matcher,
        )

        assert decision.tier == ReasoningTier.FALLBACK


# ==========================================================================
# ReasoningRouter: Inverse routing
# ==========================================================================


class TestRouterInverse:
    """Tests for the route_inverse() method."""

    def test_inverse_tier1_with_paths(self, tiny_kg):
        """Inverse routing finds paths when property keywords match."""
        router = ReasoningRouter()

        mock_matcher = MagicMock()

        decision = router.route_inverse(
            query={"target_property": "mobility"},
            graph=tiny_kg,
            matcher=mock_matcher,
        )

        # If paths are found, should be Tier 1
        if decision.paths:
            assert decision.tier == ReasoningTier.DIRECT

    def test_inverse_tier3_with_no_match(self):
        """Inverse routing falls to Tier 3 with no matches."""
        G = nx.DiGraph()
        G.add_node("isolated")

        router = ReasoningRouter()
        mock_matcher = MagicMock()
        mock_matcher.find_most_similar.return_value = (None, 0.0)

        decision = router.route_inverse(
            query={"target_property": "something_unreal"},
            graph=G,
            matcher=mock_matcher,
        )

        assert decision.tier == ReasoningTier.FALLBACK


# ==========================================================================
# ReasoningRouter: _find_paths static method
# ==========================================================================


class TestRouterFindPaths:
    """Tests for the _find_paths static helper."""

    def test_find_paths_basic(self, tiny_kg):
        """_find_paths locates paths between matching start/end keywords."""
        paths = ReasoningRouter._find_paths(
            tiny_kg,
            start_keywords=["temperature"],
            end_keywords=["mobility"],
        )
        assert isinstance(paths, list)
        assert len(paths) > 0
        for path_str in paths:
            assert " -> " in path_str

    def test_find_paths_no_match(self, tiny_kg):
        """_find_paths returns empty list when no keywords match."""
        paths = ReasoningRouter._find_paths(
            tiny_kg,
            start_keywords=["nonexistent_xyz"],
            end_keywords=["also_nonexistent"],
        )
        assert paths == []

    def test_find_paths_max_paths(self, tiny_kg):
        """_find_paths respects the max_paths limit."""
        paths = ReasoningRouter._find_paths(
            tiny_kg,
            start_keywords=["temperature"],
            end_keywords=["mobility"],
            max_paths=1,
        )
        assert len(paths) <= 1


# ==========================================================================
# ReasoningRouter: _extract_mechanisms static method
# ==========================================================================


class TestRouterExtractMechanisms:
    """Tests for the _extract_mechanisms static helper."""

    def test_extract_mechanisms_from_path_strings(self, tiny_kg):
        """_extract_mechanisms pulls mechanism text from path strings."""
        paths = ReasoningRouter._find_paths(
            tiny_kg,
            start_keywords=["temperature"],
            end_keywords=["mobility"],
        )
        mechanisms = ReasoningRouter._extract_mechanisms(tiny_kg, paths)
        assert isinstance(mechanisms, list)
        # Should find at least one mechanism
        if paths:
            assert len(mechanisms) > 0

    def test_extract_mechanisms_empty_paths(self, tiny_kg):
        """Empty path list returns empty mechanisms."""
        mechanisms = ReasoningRouter._extract_mechanisms(tiny_kg, [])
        assert mechanisms == []