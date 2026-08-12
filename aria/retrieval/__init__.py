"""ARIA retrieval module -- Path search, similarity, completeness, and ranking."""

from aria.retrieval.completeness import (
    PSPLayer,
    causal_completeness_score,
    identify_missing_layers,
    infer_required_layers,
    per_path_completeness,
)
from aria.retrieval.evidence_ranker import path_score_details, rank_paths_by_evidence
from aria.retrieval.path_search import extract_mechanisms, find_paths_for_query, find_psp_paths
from aria.retrieval.similarity import NodeMatcher

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