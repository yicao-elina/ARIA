"""ARIA retrieval module -- Path search, similarity, completeness, and ranking."""

from aria.retrieval.path_search import find_psp_paths, extract_mechanisms, find_paths_for_query
from aria.retrieval.completeness import (
    PSPLayer,
    causal_completeness_score,
    per_path_completeness,
    identify_missing_layers,
    infer_required_layers,
)
from aria.retrieval.similarity import NodeMatcher
from aria.retrieval.evidence_ranker import rank_paths_by_evidence, path_score_details

__all__ = [
    "find_psp_paths",
    "extract_mechanisms",
    "find_paths_for_query",
    "PSPLayer",
    "causal_completeness_score",
    "per_path_completeness",
    "identify_missing_layers",
    "infer_required_layers",
    "NodeMatcher",
    "rank_paths_by_evidence",
    "path_score_details",
]