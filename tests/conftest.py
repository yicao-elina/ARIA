"""
Shared pytest fixtures for ARIA test suite.

Provides reusable fixtures for small knowledge graphs, sample queries,
and ARIAResult objects that are used across multiple test modules.
"""

import json
import tempfile
from pathlib import Path

import networkx as nx
import pytest

from aria.types import (
    ARIAResult,
    CausalTraceStep,
    EngineMode,
    PSPRelationship,
    PSPType,
    ReasoningTier,
)


# ---------------------------------------------------------------------------
# Tiny KG fixture
# ---------------------------------------------------------------------------


def _build_tiny_kg() -> nx.DiGraph:
    """Build a small DiGraph with ~6 nodes for testing.

    The graph models a simplified MoS2 CVD workflow:

        CVD temperature 750C -> improved crystallinity -> higher carrier mobility
        CVD temperature 750C -> reduced defect density -> higher carrier mobility
        doping concentration Nb -> doping_level -> increased conductivity
        CVD temperature 750C -> grain growth -> improved crystallinity

    This gives 6 nodes, 5 edges, and covers all three PSP layers
    (Processing, Structure, Property).
    """
    G = nx.DiGraph()

    # Processing nodes (root -- in-degree 0)
    G.add_node("CVD temperature 750C")
    G.add_node("doping concentration Nb")

    # Structure nodes (intermediate)
    G.add_node("improved crystallinity")
    G.add_node("reduced defect density")
    G.add_node("doping_level")
    G.add_node("grain growth")

    # Property node (leaf -- out-degree 0)
    G.add_node("higher carrier mobility")

    # Processing -> Structure edges
    G.add_edge(
        "CVD temperature 750C",
        "improved crystallinity",
        mechanism="High CVD temperature promotes ordered MoS2 crystal growth",
        affected_property="crystallinity",
        source_file="mos2_cvddoping.json",
        source_doi="10.1234/mos2-cvd",
        confidence=0.9,
        psp_type=PSPType.PROCESSING_TO_STRUCTURE.value,
        relation="increases",
        psp_relationship=PSPRelationship(
            source="CVD temperature 750C",
            relation="increases",
            target="improved crystallinity",
            psp_type=PSPType.PROCESSING_TO_STRUCTURE.value,
            material="MoS2",
            evidence_text="High CVD temperature promotes ordered MoS2 crystal growth",
            paper_doi="10.1234/mos2-cvd",
            confidence=0.9,
        ).to_dict(),
    )

    G.add_edge(
        "CVD temperature 750C",
        "reduced defect density",
        mechanism="Elevated temperature anneals sulfur vacancies",
        affected_property="defect density",
        source_file="mos2_cvddoping.json",
        source_doi="10.1234/mos2-cvd",
        confidence=0.85,
        psp_type=PSPType.PROCESSING_TO_STRUCTURE.value,
        relation="decreases",
        psp_relationship=PSPRelationship(
            source="CVD temperature 750C",
            relation="decreases",
            target="reduced defect density",
            psp_type=PSPType.PROCESSING_TO_STRUCTURE.value,
            material="MoS2",
            evidence_text="Elevated temperature anneals sulfur vacancies",
            paper_doi="10.1234/mos2-cvd",
            confidence=0.85,
        ).to_dict(),
    )

    G.add_edge(
        "doping concentration Nb",
        "doping_level",
        mechanism="Nb substitution at Mo sites introduces carriers",
        affected_property="doping_level",
        source_file="mos2_cvddoping.json",
        source_doi="10.5678/nb-doping",
        confidence=0.92,
        psp_type=PSPType.PROCESSING_TO_STRUCTURE.value,
        relation="increases",
        psp_relationship=PSPRelationship(
            source="doping concentration Nb",
            relation="increases",
            target="doping_level",
            psp_type=PSPType.PROCESSING_TO_STRUCTURE.value,
            material="MoS2",
            evidence_text="Nb substitution at Mo sites introduces carriers",
            paper_doi="10.5678/nb-doping",
            confidence=0.92,
        ).to_dict(),
    )

    # Structure -> Structure edges
    G.add_edge(
        "CVD temperature 750C",
        "grain growth",
        mechanism="Higher temperature increases grain size",
        affected_property="grain_size",
        source_file="mos2_cvddoping.json",
        source_doi="10.1234/mos2-cvd",
        confidence=0.8,
        psp_type=PSPType.PROCESSING_TO_STRUCTURE.value,
        relation="increases",
        psp_relationship=PSPRelationship(
            source="CVD temperature 750C",
            relation="increases",
            target="grain growth",
            psp_type=PSPType.PROCESSING_TO_STRUCTURE.value,
            material="MoS2",
            evidence_text="Higher temperature increases grain size",
            confidence=0.8,
        ).to_dict(),
    )

    G.add_edge(
        "grain growth",
        "improved crystallinity",
        mechanism="Larger grains reduce grain boundary scattering",
        affected_property="crystallinity",
        source_file="mos2_cvddoping.json",
        source_doi="10.1234/mos2-cvd",
        confidence=0.75,
        psp_type=PSPType.STRUCTURE_TO_STRUCTURE.value,
        relation="increases",
        psp_relationship=PSPRelationship(
            source="grain growth",
            relation="increases",
            target="improved crystallinity",
            psp_type=PSPType.STRUCTURE_TO_STRUCTURE.value,
            material="MoS2",
            evidence_text="Larger grains reduce grain boundary scattering",
            confidence=0.75,
        ).to_dict(),
    )

    # Structure -> Property edges
    G.add_edge(
        "improved crystallinity",
        "higher carrier mobility",
        mechanism="Ordered crystal lattice enables efficient carrier transport",
        affected_property="carrier mobility",
        source_file="mos2_cvddoping.json",
        source_doi="10.1234/mos2-cvd",
        confidence=0.88,
        psp_type=PSPType.STRUCTURE_TO_PROPERTY.value,
        relation="increases",
        psp_relationship=PSPRelationship(
            source="improved crystallinity",
            relation="increases",
            target="higher carrier mobility",
            psp_type=PSPType.STRUCTURE_TO_PROPERTY.value,
            material="MoS2",
            evidence_text="Ordered crystal lattice enables efficient carrier transport",
            paper_doi="10.1234/mos2-cvd",
            confidence=0.88,
        ).to_dict(),
    )

    G.add_edge(
        "reduced defect density",
        "higher carrier mobility",
        mechanism="Fewer scattering centres boost mobility",
        affected_property="carrier mobility",
        source_file="mos2_cvddoping.json",
        source_doi="10.5678/nb-doping",
        confidence=0.82,
        psp_type=PSPType.STRUCTURE_TO_PROPERTY.value,
        relation="increases",
        psp_relationship=PSPRelationship(
            source="reduced defect density",
            relation="increases",
            target="higher carrier mobility",
            psp_type=PSPType.STRUCTURE_TO_PROPERTY.value,
            material="MoS2",
            evidence_text="Fewer scattering centres boost mobility",
            paper_doi="10.5678/nb-doping",
            confidence=0.82,
        ).to_dict(),
    )

    return G


@pytest.fixture
def tiny_kg() -> nx.DiGraph:
    """Return a small NetworkX DiGraph with ~7 nodes for testing."""
    return _build_tiny_kg()


@pytest.fixture
def tiny_kg_json_file(tmp_path: Path) -> Path:
    """Write a tiny KG in the enriched JSON format and return the path.

    This file can be used to test ``load_kg`` without relying on
    external data files.
    """
    relationships = [
        {
            "cause_parameter": "CVD temperature 750C",
            "effect_on_doping": "improved crystallinity",
            "affected_property": "crystallinity",
            "mechanism_quote": "High CVD temperature promotes ordered crystal growth",
            "confidence_level": "high",
            "source_file": "mos2_cvddoping.json",
            "source_doi": "10.1234/mos2-cvd",
            "relationship_id": "rel_001",
        },
        {
            "cause_parameter": "improved crystallinity",
            "effect_on_doping": "higher carrier mobility",
            "affected_property": "carrier mobility",
            "mechanism_quote": "Ordered lattice enables efficient carrier transport",
            "confidence_level": "experimentally verified",
            "source_file": "mos2_cvddoping.json",
            "source_doi": "10.1234/mos2-cvd",
            "relationship_id": "rel_002",
        },
        {
            "cause_parameter": "doping concentration Nb",
            "effect_on_doping": "increased conductivity",
            "affected_property": "conductivity",
            "mechanism_quote": "Nb substitution introduces carriers",
            "confidence_level": "moderate",
            "source_file": "ws2_doping.json",
            "source_doi": "10.5678/nb-doping",
            "relationship_id": "rel_003",
        },
    ]
    payload = {"causal_relationships": relationships}
    kg_file = tmp_path / "tiny_kg.json"
    kg_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return kg_file


@pytest.fixture
def sample_query() -> dict:
    """Return a sample forward-prediction query dict."""
    return {
        "material": "MoS2",
        "method": "CVD",
        "temperature": "750C",
    }


@pytest.fixture
def sample_inverse_query() -> dict:
    """Return a sample inverse-design query dict."""
    return {
        "target_material": "MoS2",
        "target_property": "high n-type mobility",
        "method": "CVD",
    }


@pytest.fixture
def sample_aria_result() -> ARIAResult:
    """Return a sample ARIAResult for testing."""
    return ARIAResult(
        answer={"carrier_type": "n-type", "mobility": "50 cm2/Vs"},
        tier=ReasoningTier.DIRECT,
        confidence=0.85,
        reasoning_type="direct_path",
        causal_trace=[
            CausalTraceStep(
                processing="CVD temperature 750C",
                structure="improved crystallinity",
                property_="higher carrier mobility",
                evidence_text="High CVD temperature promotes ordered crystal growth",
                confidence=0.9,
            ),
        ],
        missing_evidence=[],
        kg_paths_used=2,
        kg_paths=["CVD temperature 750C -> improved crystallinity -> higher carrier mobility"],
        literature_papers=[],
        source_attribution={},
        mode="aria",
        model="qwen2:7b",
        latency_ms=1234.5,
    )