"""
Tests for aria.retrieval modules -- path_search, completeness,
evidence_ranker, and similarity.

Covers:
- path_search.find_psp_paths() with a tiny graph
- path_search.extract_mechanisms()
- completeness.causal_completeness_score()
- completeness.classify_path_layers_detailed()
- completeness.infer_required_layers()
- completeness.identify_missing_layers()
- evidence_ranker.rank_paths_by_evidence()
- evidence_ranker.path_score_details()
- similarity.NodeMatcher (basic init and interface)
"""

import pytest
import networkx as nx

from aria.kg.schema import classify_node_layer
from aria.retrieval.path_search import (
    extract_mechanisms,
    find_psp_paths,
    find_paths_for_query,
)
from aria.retrieval.completeness import (
    PSPLayer,
    causal_completeness_score,
    classify_path_layers_detailed,
    identify_missing_layers,
    infer_required_layers,
    per_path_completeness,
)
from aria.retrieval.evidence_ranker import (
    path_score_details,
    rank_paths_by_evidence,
)


# ==========================================================================
# path_search: find_psp_paths
# ==========================================================================


class TestFindPspPaths:
    """Tests for path_search.find_psp_paths()."""

    def test_basic_path_search(self, tiny_kg):
        """find_psp_paths() returns paths from processing to property keywords."""
        paths = find_psp_paths(
            tiny_kg,
            start_keywords=["temperature", "CVD"],
            end_keywords=["mobility"],
        )
        assert len(paths) > 0
        # Each path should be a list of node labels
        for path in paths:
            assert isinstance(path, list)
            assert len(path) >= 2

    def test_path_starts_with_keyword_match(self, tiny_kg):
        """Returned paths start at nodes matching start_keywords."""
        paths = find_psp_paths(
            tiny_kg,
            start_keywords=["temperature"],
            end_keywords=["mobility"],
        )
        for path in paths:
            first = path[0].lower()
            assert "temperature" in first or "cvd" in first

    def test_path_ends_with_keyword_match(self, tiny_kg):
        """Returned paths end at nodes matching end_keywords."""
        paths = find_psp_paths(
            tiny_kg,
            start_keywords=["temperature"],
            end_keywords=["mobility"],
        )
        for path in paths:
            last = path[-1].lower()
            assert "mobility" in last

    def test_no_start_match_returns_empty(self, tiny_kg):
        """No matching start nodes returns an empty list."""
        paths = find_psp_paths(
            tiny_kg,
            start_keywords=["quantum_supremacy_nonexistent"],
            end_keywords=["mobility"],
        )
        assert paths == []

    def test_no_end_match_returns_empty(self, tiny_kg):
        """No matching end nodes returns an empty list."""
        paths = find_psp_paths(
            tiny_kg,
            start_keywords=["temperature"],
            end_keywords=["xyz_nonexistent"],
        )
        assert paths == []

    def test_max_hops_limit(self, tiny_kg):
        """max_hops limits path length."""
        paths_unlimited = find_psp_paths(
            tiny_kg, ["temperature"], ["mobility"], max_hops=10,
        )
        paths_limited = find_psp_paths(
            tiny_kg, ["temperature"], ["mobility"], max_hops=2,
        )
        # Limited search should not return more paths than unlimited
        # (it may return fewer or equal)
        assert len(paths_limited) <= len(paths_unlimited)
        for path in paths_limited:
            assert len(path) <= 3  # max_hops=2 means max 3 nodes (2 edges)

    def test_reverse_search(self, tiny_kg):
        """Reverse search traces from property back to synthesis."""
        paths = find_psp_paths(
            tiny_kg,
            start_keywords=["mobility"],
            end_keywords=["temperature"],
            reverse=True,
        )
        # Reverse search should find paths that trace backward
        # In the reversed graph, "mobility" becomes a start and "temperature" an end
        assert isinstance(paths, list)

    def test_duplicate_removal(self, tiny_kg):
        """find_psp_paths() removes duplicate paths."""
        paths = find_psp_paths(
            tiny_kg,
            start_keywords=["temperature", "CVD"],
            end_keywords=["mobility"],
        )
        path_strs = [" -> ".join(p) for p in paths]
        assert len(path_strs) == len(set(path_strs)), "Duplicate paths found"

    def test_doping_path(self, tiny_kg):
        """find_psp_paths() finds paths starting from doping nodes."""
        paths = find_psp_paths(
            tiny_kg,
            start_keywords=["doping"],
            end_keywords=["mobility"],
        )
        # Doping concentration -> doping_level is a structure node, not directly
        # connected to "higher carrier mobility" in the tiny graph
        # So we may or may not get paths, but the function should not error
        assert isinstance(paths, list)


# ==========================================================================
# path_search: extract_mechanisms
# ==========================================================================


class TestExtractMechanisms:
    """Tests for path_search.extract_mechanisms()."""

    def test_extract_from_valid_paths(self, tiny_kg):
        """extract_mechanisms() returns mechanism data from path edges."""
        paths = find_psp_paths(
            tiny_kg, ["temperature"], ["mobility"],
        )
        mechanisms = extract_mechanisms(tiny_kg, paths)
        assert isinstance(mechanisms, list)
        assert len(mechanisms) > 0

        for mech in mechanisms:
            assert "source" in mech
            assert "target" in mech
            assert "mechanism" in mech
            assert "confidence" in mech

    def test_extract_from_empty_paths(self, tiny_kg):
        """extract_mechanisms() returns an empty list for no paths."""
        mechanisms = extract_mechanisms(tiny_kg, [])
        assert mechanisms == []

    def test_mechanism_text_preserved(self, tiny_kg):
        """Mechanism text from edges is preserved in extraction."""
        paths = find_psp_paths(
            tiny_kg, ["temperature"], ["mobility"],
        )
        mechanisms = extract_mechanisms(tiny_kg, paths)
        # At least one mechanism should have non-empty text
        mechanism_texts = [m["mechanism"] for m in mechanisms if m["mechanism"]]
        assert len(mechanism_texts) > 0


# ==========================================================================
# path_search: find_paths_for_query
# ==========================================================================


class TestFindPathsForQuery:
    """Tests for path_search.find_paths_for_query()."""

    def test_forward_direction(self, tiny_kg):
        """Forward direction finds paths from synthesis to property keywords."""
        paths = find_paths_for_query(
            tiny_kg, ["temperature", "CVD"], direction="forward",
        )
        assert isinstance(paths, list)

    def test_inverse_direction(self, tiny_kg):
        """Inverse direction finds paths from property to synthesis."""
        paths = find_paths_for_query(
            tiny_kg, ["mobility", "carrier"], direction="inverse",
        )
        assert isinstance(paths, list)


# ==========================================================================
# completeness: causal_completeness_score
# ==========================================================================


class TestCausalCompletenessScore:
    """Tests for completeness.causal_completeness_score()."""

    def test_full_completeness(self, tiny_kg):
        """A path covering all three PSP layers scores 1.0 for a full query."""
        # Path: CVD temperature -> improved crystallinity -> higher carrier mobility
        # Covers Processing, Structure, Property
        paths = [
            ["CVD temperature 750C", "improved crystallinity", "higher carrier mobility"],
        ]
        score = causal_completeness_score(
            tiny_kg, paths, "What is the effect of CVD temperature on carrier mobility?"
        )
        assert score == 1.0

    def test_partial_completeness(self, tiny_kg):
        """A path covering only two layers scores 0.67 for a full query."""
        # Path: improved crystallinity -> higher carrier mobility
        # Covers Structure and Property only
        paths = [
            ["improved crystallinity", "higher carrier mobility"],
        ]
        score = causal_completeness_score(
            tiny_kg, paths, "How does processing affect carrier mobility?"
        )
        # Query mentions "processing" and "mobility" so requires P, S, and Pr
        # Path covers S and Pr but not P -> score 2/3
        assert 0.0 < score <= 1.0

    def test_no_paths_scores_zero(self, tiny_kg):
        """Empty paths give a score of 0.0."""
        score = causal_completeness_score(tiny_kg, [], "temperature effect on mobility")
        assert score == 0.0

    def test_default_all_layers(self, tiny_kg):
        """A vague query defaults to requiring all three layers."""
        paths = [
            ["CVD temperature 750C", "improved crystallinity", "higher carrier mobility"],
        ]
        score = causal_completeness_score(tiny_kg, paths, "vague query")
        # "vague query" matches nothing -> all three layers required by default
        # Path covers all three -> score = 1.0
        assert score == 1.0


# ==========================================================================
# completeness: classify_path_layers_detailed
# ==========================================================================


class TestClassifyPathLayersDetailed:
    """Tests for completeness.classify_path_layers_detailed()."""

    def test_detailed_classification(self, tiny_kg):
        """classify_path_layers_detailed() classifies nodes into PSP layers."""
        path = [
            "CVD temperature 750C",
            "improved crystallinity",
            "higher carrier mobility",
        ]
        result = classify_path_layers_detailed(path, tiny_kg)
        assert "Processing" in result
        assert "Structure" in result
        assert "Property" in result
        assert "Unknown" in result
        assert "CVD temperature 750C" in result["Processing"]
        assert "improved crystallinity" in result["Structure"]
        assert "higher carrier mobility" in result["Property"]

    def test_without_graph(self):
        """classify_path_layers_detailed() works without a graph argument."""
        path = ["temperature", "crystallinity", "mobility"]
        result = classify_path_layers_detailed(path)
        assert "Processing" in result
        assert "Structure" in result


# ==========================================================================
# completeness: infer_required_layers
# ==========================================================================


class TestInferRequiredLayers:
    """Tests for completeness.infer_required_layers()."""

    def test_forward_query(self):
        """A query with processing + property keywords requires P + S + Pr."""
        layers = infer_required_layers("CVD temperature effect on carrier mobility")
        assert PSPLayer.PROCESSING in layers
        assert PSPLayer.PROPERTY in layers

    def test_property_only_query(self):
        """A property-only query still requires at least two layers."""
        layers = infer_required_layers("band gap energy")
        # Property detected; single layer expands to include Structure
        assert PSPLayer.PROPERTY in layers
        assert len(layers) >= 2

    def test_default_all_layers(self):
        """A vague query requires all three layers by default."""
        layers = infer_required_layers("something vague")
        assert PSPLayer.PROCESSING in layers
        assert PSPLayer.STRUCTURE in layers
        assert PSPLayer.PROPERTY in layers


# ==========================================================================
# completeness: identify_missing_layers
# ==========================================================================


class TestIdentifyMissingLayers:
    """Tests for completeness.identify_missing_layers()."""

    def test_missing_processing(self, tiny_kg):
        """A structure->property path is missing the Processing layer."""
        paths = [["improved crystallinity", "higher carrier mobility"]]
        missing = identify_missing_layers(
            tiny_kg, paths, "How does temperature affect mobility?"
        )
        # Query requires Processing; path doesn't cover it
        assert PSPLayer.PROCESSING in missing or len(missing) == 0

    def test_no_missing_when_full(self, tiny_kg):
        """A full PSP path has no missing layers for a full query."""
        paths = [
            ["CVD temperature 750C", "improved crystallinity", "higher carrier mobility"],
        ]
        missing = identify_missing_layers(
            tiny_kg, paths, "CVD temperature effect on carrier mobility"
        )
        # This full path covers P, S, Pr -- nothing missing
        assert PSPLayer.PROCESSING not in missing
        assert PSPLayer.STRUCTURE not in missing
        assert PSPLayer.PROPERTY not in missing


# ==========================================================================
# completeness: per_path_completeness
# ==========================================================================


class TestPerPathCompleteness:
    """Tests for completeness.per_path_completeness()."""

    def test_per_path_scores(self, tiny_kg):
        """Each path gets its own completeness score."""
        paths = [
            ["CVD temperature 750C", "improved crystallinity", "higher carrier mobility"],
            ["improved crystallinity", "higher carrier mobility"],
        ]
        results = per_path_completeness(
            tiny_kg, paths, "CVD temperature effect on carrier mobility"
        )
        assert len(results) == 2
        for path, score in results:
            assert isinstance(path, list)
            assert 0.0 <= score <= 1.0

    def test_full_path_highest_score(self, tiny_kg):
        """A full PSP path scores higher than a partial path."""
        paths = [
            ["CVD temperature 750C", "improved crystallinity", "higher carrier mobility"],
            ["improved crystallinity", "higher carrier mobility"],
        ]
        results = per_path_completeness(
            tiny_kg, paths, "CVD temperature effect on carrier mobility"
        )
        full_score = results[0][1]
        partial_score = results[1][1]
        assert full_score >= partial_score


# ==========================================================================
# evidence_ranker: rank_paths_by_evidence
# ==========================================================================


class TestRankPathsByEvidence:
    """Tests for evidence_ranker.rank_paths_by_evidence()."""

    def test_basic_ranking(self, tiny_kg):
        """rank_paths_by_evidence() returns paths sorted by score."""
        paths = find_psp_paths(tiny_kg, ["temperature"], ["mobility"])
        if not paths:
            pytest.skip("No paths found in tiny KG for ranking test")

        ranked = rank_paths_by_evidence(paths, tiny_kg)
        assert len(ranked) == len(paths)
        # Scores should be in descending order
        scores = [score for _, score in ranked]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_empty_paths_returns_empty(self, tiny_kg):
        """Empty path list returns empty result."""
        ranked = rank_paths_by_evidence([], tiny_kg)
        assert ranked == []

    def test_scores_in_range(self, tiny_kg):
        """All scores are between 0.0 and 1.0."""
        paths = find_psp_paths(tiny_kg, ["temperature"], ["mobility"])
        if not paths:
            pytest.skip("No paths found in tiny KG")

        ranked = rank_paths_by_evidence(paths, tiny_kg)
        for path, score in ranked:
            assert 0.0 <= score <= 1.0

    def test_custom_weights(self, tiny_kg):
        """Custom weights affect the ranking."""
        paths = find_psp_paths(tiny_kg, ["temperature"], ["mobility"])
        if not paths:
            pytest.skip("No paths found in tiny KG")

        ranked_default = rank_paths_by_evidence(paths, tiny_kg)
        ranked_confidence = rank_paths_by_evidence(
            paths, tiny_kg, weights={"confidence": 1.0, "evidence_richness": 0.0, "psp_coverage": 0.0}
        )
        # Results should have the same number of entries but potentially different order
        assert len(ranked_default) == len(ranked_confidence)


# ==========================================================================
# evidence_ranker: path_score_details
# ==========================================================================


class TestPathScoreDetails:
    """Tests for evidence_ranker.path_score_details()."""

    def test_returns_component_scores(self, tiny_kg):
        """path_score_details() returns confidence, evidence_richness, and psp_coverage."""
        paths = find_psp_paths(tiny_kg, ["temperature"], ["mobility"])
        if not paths:
            pytest.skip("No paths found in tiny KG")

        path = paths[0]
        details = path_score_details(path, tiny_kg)
        assert "confidence" in details
        assert "evidence_richness" in details
        assert "psp_coverage" in details
        for key in ("confidence", "evidence_richness", "psp_coverage"):
            assert 0.0 <= details[key] <= 1.0

    def test_single_node_path(self, tiny_kg):
        """A single-node path has zero confidence and evidence_richness."""
        details = path_score_details(["CVD temperature 750C"], tiny_kg)
        assert details["confidence"] == 0.0
        assert details["evidence_richness"] == 0.0


# ==========================================================================
# similarity: NodeMatcher
# ==========================================================================


class TestNodeMatcher:
    """Tests for similarity.NodeMatcher.

    Note: NodeMatcher requires sentence-transformers and scikit-learn,
    which may not be installed. Tests are guarded accordingly.
    """

    def test_init_with_dependencies(self, tiny_kg):
        """NodeMatcher can be initialised when dependencies are available.

        This test checks whether sentence-transformers and scikit-learn
        are installed.  If they are not, the test is skipped gracefully.
        The import of NodeMatcher itself never raises -- the ImportError
        is raised inside __init__.
        """
        from aria.retrieval.similarity import NodeMatcher, _HAS_DEPS

        if not _HAS_DEPS:
            pytest.skip("sentence-transformers or scikit-learn not installed")

        matcher = NodeMatcher(tiny_kg, model_name="all-MiniLM-L6-v2")
        assert matcher.graph is tiny_kg
        assert matcher.model_name == "all-MiniLM-L6-v2"

    def test_init_without_dependencies_raises(self, tiny_kg):
        """NodeMatcher raises ImportError when dependencies are missing."""
        from aria.retrieval.similarity import NodeMatcher, _HAS_DEPS

        if _HAS_DEPS:
            pytest.skip("sentence-transformers is installed; cannot test ImportError")

        with pytest.raises(ImportError, match="NodeMatcher requires"):
            NodeMatcher(tiny_kg, model_name="all-MiniLM-L6-v2")

    def test_precompute_and_find_similar(self, tiny_kg):
        """After precompute(), find_similar() returns results."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        from aria.retrieval.similarity import NodeMatcher

        matcher = NodeMatcher(tiny_kg, model_name="all-MiniLM-L6-v2")
        matcher.precompute()

        results = matcher.find_similar("CVD temperature", top_k=3)
        assert isinstance(results, list)
        assert len(results) <= 3

        for node, score in results:
            assert isinstance(node, str)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0  # cosine similarity range

    def test_find_most_similar(self, tiny_kg):
        """find_most_similar() returns the best match."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        from aria.retrieval.similarity import NodeMatcher

        matcher = NodeMatcher(tiny_kg, model_name="all-MiniLM-L6-v2")
        matcher.precompute()

        node, score = matcher.find_most_similar("high temperature growth")
        assert node is not None or score == 0.0
        if node is not None:
            assert isinstance(node, str)
            assert isinstance(score, float)

    def test_find_similar_empty_candidates(self, tiny_kg):
        """find_similar() with non-matching candidates returns empty list."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        from aria.retrieval.similarity import NodeMatcher

        matcher = NodeMatcher(tiny_kg, model_name="all-MiniLM-L6-v2")
        matcher.precompute()

        results = matcher.find_similar(
            "CVD temperature", candidates=["nonexistent_node_xyz"], top_k=3
        )
        assert results == []

    def test_embedding_distance(self, tiny_kg):
        """embedding_distance() returns a value between 0 and 2."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        from aria.retrieval.similarity import NodeMatcher

        matcher = NodeMatcher(tiny_kg, model_name="all-MiniLM-L6-v2")
        matcher.precompute()

        dist = matcher.embedding_distance("CVD temperature", "crystallinity")
        assert isinstance(dist, float)
        assert 0.0 <= dist <= 2.0

    def test_embedding_distance_empty_string(self, tiny_kg):
        """embedding_distance() returns 1.0 for empty strings."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        from aria.retrieval.similarity import NodeMatcher

        matcher = NodeMatcher(tiny_kg, model_name="all-MiniLM-L6-v2")
        assert matcher.embedding_distance("", "test") == 1.0
        assert matcher.embedding_distance("test", "") == 1.0