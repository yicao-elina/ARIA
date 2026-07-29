"""Tests for aria.cli.formatting."""

from aria.types import ARIAResult, ChainOfThought, ReasoningStep, ReasoningTier
from aria.cli.formatting import format_diagnostics_report, format_explain, format_result_summary


def _make_result(**overrides) -> ARIAResult:
    defaults = dict(
        answer={"carrier_mobility": "high"},
        tier=ReasoningTier.DIRECT,
        confidence=0.85,
        reasoning_type="direct_path",
        causal_trace=[],
        missing_evidence=[],
        kg_paths_used=2,
        kg_paths=["A -> B -> C"],
        literature_papers=[],
        source_attribution={},
        chain_of_thought=None,
        mode="aria",
        model="qwen2:7b",
        latency_ms=123.4,
    )
    defaults.update(overrides)
    return ARIAResult(**defaults)


def test_format_result_summary_includes_key_fields():
    result = _make_result()
    text = format_result_summary(result)
    assert "DIRECT" in text
    assert "0.85" in text
    assert "carrier_mobility" in text


def test_format_result_summary_lists_missing_evidence():
    result = _make_result(missing_evidence=["no crystallinity data"])
    text = format_result_summary(result)
    assert "no crystallinity data" in text


def test_format_explain_without_chain_of_thought():
    result = _make_result(chain_of_thought=None)
    text = format_explain(result)
    assert "No chain-of-thought available" in text


def test_format_explain_with_chain_of_thought():
    cot = ChainOfThought(
        reasoning_steps=[
            ReasoningStep(
                step_id="kg_retrieval",
                description="Found 2 paths",
                confidence=1.0,
                intermediate_conclusion="Tier 1 selected",
            )
        ],
    )
    result = _make_result(chain_of_thought=cot)
    text = format_explain(result)
    assert "kg_retrieval" in text
    assert "Tier 1 selected" in text


def test_format_diagnostics_report_renders_structure_section():
    report = {
        "kg_file": "demo.json",
        "structure": {
            "num_nodes": 10, "num_edges": 5, "density": 0.1, "avg_degree": 1.0,
            "num_root_nodes": 2, "num_leaf_nodes": 3, "num_intermediate_nodes": 5,
            "is_dag": True, "longest_path_length": 3, "weakly_connected_components": 1,
        },
        "content": {
            "mechanism_coverage": 0.5, "edges_with_mechanism": 2, "edges_without_mechanism": 3,
            "avg_mechanism_length": 20.0, "property_coverage": 0.4, "avg_confidence": 0.9,
            "num_unique_properties": 3,
        },
        "coverage": {
            "total_queries": 5, "queries_with_match": 3, "queries_without_match": 2,
            "avg_paths_per_query": 1.2, "coverage_rate": 0.6,
        },
        "diversity": {"diversity_score": 0.7, "avg_similarity": 0.3},
        "gaps": {
            "current_coverage": 0.6,
            "coverage_estimates": {"50%_coverage": {"additional_edges_needed": 0}},
            "papers_needed_estimates": {},
            "recommendation": "GOOD: Good size and coverage.",
        },
    }
    text = format_diagnostics_report(report)
    assert "KNOWLEDGE GRAPH QUALITY DIAGNOSTIC REPORT" in text
    assert "GOOD: Good size and coverage." in text
