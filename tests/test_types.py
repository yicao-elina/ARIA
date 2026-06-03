"""
Tests for aria.types -- data types, enums, and inference helpers.

Covers:
- PSPRelationship creation and from_legacy() conversion
- ARIAResult creation and to_dict()
- ReasoningTier and EngineMode enums
- CausalTraceStep creation
- _infer_relation(), _infer_psp_type(), _parse_confidence()
- _infer_material() helper
"""

import pytest

from aria.types import (
    ARIAResult,
    CausalTraceStep,
    ChainOfThought,
    EngineMode,
    KnowledgeSource,
    PSPRelationship,
    PSPType,
    ReasoningStep,
    ReasoningTier,
    _infer_material,
    _infer_psp_type,
    _infer_relation,
    _parse_confidence,
)


# ==========================================================================
# PSPRelationship
# ==========================================================================


class TestPSPRelationship:
    """Tests for the PSPRelationship dataclass."""

    def test_creation_defaults(self):
        """PSPRelationship stores all fields, with sensible defaults."""
        rel = PSPRelationship(
            source="CVD temperature 750C",
            relation="increases",
            target="improved crystallinity",
            psp_type=PSPType.PROCESSING_TO_STRUCTURE.value,
        )
        assert rel.source == "CVD temperature 750C"
        assert rel.relation == "increases"
        assert rel.target == "improved crystallinity"
        assert rel.psp_type == "Processing_to_Structure"
        assert rel.material == ""
        assert rel.evidence_text is None
        assert rel.paper_doi is None
        assert rel.confidence == 1.0
        assert rel.curation == "extracted"
        assert rel.relationship_id is None

    def test_creation_full(self):
        """PSPRelationship with all fields explicitly set."""
        rel = PSPRelationship(
            source="doping concentration Nb",
            relation="induces",
            target="increased conductivity",
            psp_type=PSPType.PROCESSING_TO_PROPERTY.value,
            material="MoS2",
            evidence_text="Nb substitution introduces carriers",
            paper_doi="10.1234/test",
            confidence=0.88,
            curation="expert_verified",
            relationship_id="rel_042",
        )
        assert rel.material == "MoS2"
        assert rel.evidence_text == "Nb substitution introduces carriers"
        assert rel.paper_doi == "10.1234/test"
        assert rel.confidence == 0.88
        assert rel.curation == "expert_verified"
        assert rel.relationship_id == "rel_042"

    def test_to_dict(self):
        """to_dict() returns a dict with all fields."""
        rel = PSPRelationship(
            source="A", relation="increases", target="B",
            psp_type=PSPType.STRUCTURE_TO_PROPERTY.value,
            material="MoS2",
        )
        d = rel.to_dict()
        assert isinstance(d, dict)
        assert d["source"] == "A"
        assert d["relation"] == "increases"
        assert d["target"] == "B"
        assert d["psp_type"] == "Structure_to_Property"
        assert d["material"] == "MoS2"
        assert d["confidence"] == 1.0  # default

    def test_from_legacy_basic(self):
        """from_legacy() correctly maps legacy field names."""
        legacy = {
            "cause_parameter": "CVD temperature 750C",
            "effect_on_doping": "increases carrier mobility",
            "affected_property": "carrier mobility",
            "mechanism_quote": "Thermal activation of carriers",
            "confidence_level": "high",
            "source_file": "mos2_cvddoping.json",
            "paper_doi": "10.1234/mos2",
            "relationship_id": "rel_001",
        }
        rel = PSPRelationship.from_legacy(legacy)
        assert rel.source == "CVD temperature 750C"
        assert rel.target == "carrier mobility"
        assert rel.evidence_text == "Thermal activation of carriers"
        assert rel.paper_doi == "10.1234/mos2"
        assert rel.curation == "extracted"
        assert rel.relationship_id == "rel_001"

    def test_from_legacy_infer_relation_increases(self):
        """from_legacy() infers 'increases' from 'increases' in effect text."""
        legacy = {
            "cause_parameter": "temperature",
            "effect_on_doping": "increases doping",
            "affected_property": "doping level",
        }
        rel = PSPRelationship.from_legacy(legacy)
        assert rel.relation == "increases"

    def test_from_legacy_infer_relation_decreases(self):
        """from_legacy() infers 'decreases' from 'reduces' in effect text."""
        legacy = {
            "cause_parameter": "annealing",
            "effect_on_doping": "reduces defects",
            "affected_property": "defect density",
        }
        rel = PSPRelationship.from_legacy(legacy)
        assert rel.relation == "decreases"

    def test_from_legacy_infer_relation_induces(self):
        """from_legacy() infers 'induces' from 'causes' in effect text."""
        legacy = {
            "cause_parameter": "pressure",
            "effect_on_doping": "causes phase change",
            "affected_property": "phase",
        }
        rel = PSPRelationship.from_legacy(legacy)
        assert rel.relation == "induces"

    def test_from_legacy_infer_relation_inhibits(self):
        """from_legacy() infers 'inhibits' from 'prevents' in effect text."""
        legacy = {
            "cause_parameter": "doping",
            "effect_on_doping": "inhibits carrier scattering",
            "affected_property": "scattering",
        }
        rel = PSPRelationship.from_legacy(legacy)
        assert rel.relation == "inhibits"

    def test_from_legacy_infer_relation_fallback(self):
        """from_legacy() falls back to 'affects' for unrecognised effect text."""
        legacy = {
            "cause_parameter": "substrate",
            "effect_on_doping": "modulates growth",
            "affected_property": "growth rate",
        }
        rel = PSPRelationship.from_legacy(legacy)
        assert rel.relation == "affects"

    def test_from_legacy_infer_psp_type(self):
        """from_legacy() infers PSP type from cause and effect keywords."""
        # Processing -> Structure
        legacy = {
            "cause_parameter": "CVD temperature",
            "effect_on_doping": "changes crystallinity",
            "affected_property": "crystallinity",
        }
        rel = PSPRelationship.from_legacy(legacy)
        assert rel.psp_type == PSPType.PROCESSING_TO_STRUCTURE.value

    def test_from_legacy_missing_fields(self):
        """from_legacy() handles missing optional fields gracefully."""
        legacy = {
            "cause_parameter": "temperature",
            "effect_on_doping": "increases mobility",
        }
        rel = PSPRelationship.from_legacy(legacy)
        assert rel.source == "temperature"
        assert rel.target == "increases mobility"
        assert rel.evidence_text is None
        assert rel.paper_doi is None

    def test_from_legacy_empty_effect(self):
        """from_legacy() with empty effect_on_doping falls back to affected_property."""
        legacy = {
            "cause_parameter": "temperature",
            "effect_on_doping": "",
            "affected_property": "conductivity",
        }
        rel = PSPRelationship.from_legacy(legacy)
        # Empty string for effect_on_doping is stripped to ""
        assert rel.target == "conductivity"


# ==========================================================================
# CausalTraceStep
# ==========================================================================


class TestCausalTraceStep:
    """Tests for the CausalTraceStep dataclass."""

    def test_creation_required_fields(self):
        """CausalTraceStep stores the three core fields."""
        step = CausalTraceStep(
            processing="CVD 750C",
            structure="improved crystallinity",
            property_="higher mobility",
        )
        assert step.processing == "CVD 750C"
        assert step.structure == "improved crystallinity"
        assert step.property_ == "higher mobility"
        assert step.evidence_text is None
        assert step.confidence == 1.0

    def test_creation_all_fields(self):
        """CausalTraceStep with optional fields populated."""
        step = CausalTraceStep(
            processing="CVD 750C",
            structure="improved crystallinity",
            property_="higher mobility",
            evidence_text="High temp promotes crystal growth",
            evidence_doi="10.1234/test",
            confidence=0.88,
        )
        assert step.evidence_text == "High temp promotes crystal growth"
        assert step.evidence_doi == "10.1234/test"
        assert step.confidence == 0.88

    def test_to_dict(self):
        """to_dict() includes all fields."""
        step = CausalTraceStep(
            processing="A", structure="B", property_="C",
            confidence=0.7,
        )
        d = step.to_dict()
        assert d["processing"] == "A"
        assert d["structure"] == "B"
        assert d["property_"] == "C"
        assert d["confidence"] == 0.7
        assert d["evidence_text"] is None


# ==========================================================================
# ARIAResult
# ==========================================================================


class TestARIAResult:
    """Tests for the ARIAResult dataclass."""

    def test_creation_minimal(self):
        """ARIAResult with required fields and defaults."""
        result = ARIAResult(
            answer={"mobility": "50 cm2/Vs"},
            tier=ReasoningTier.DIRECT,
            confidence=0.85,
            reasoning_type="direct_path",
        )
        assert result.answer == {"mobility": "50 cm2/Vs"}
        assert result.tier == ReasoningTier.DIRECT
        assert result.confidence == 0.85
        assert result.reasoning_type == "direct_path"
        assert result.causal_trace == []
        assert result.missing_evidence == []
        assert result.kg_paths_used == 0
        assert result.kg_paths == []
        assert result.literature_papers == []
        assert result.source_attribution == {}
        assert result.chain_of_thought is None
        assert result.mode == ""
        assert result.model == ""
        assert result.latency_ms == 0.0

    def test_creation_full(self):
        """ARIAResult with all fields populated."""
        step = CausalTraceStep(
            processing="A", structure="B", property_="C",
        )
        result = ARIAResult(
            answer={"mobility": "50 cm2/Vs"},
            tier=ReasoningTier.ANALOGICAL,
            confidence=0.72,
            reasoning_type="transfer_learning",
            causal_trace=[step],
            missing_evidence=["defect density"],
            kg_paths_used=1,
            kg_paths=["A -> B -> C"],
            literature_papers=[{"title": "Test Paper", "year": 2024}],
            source_attribution={"kg_sources": 3},
            mode="aria",
            model="qwen2:7b",
            latency_ms=2500.0,
        )
        assert result.tier == ReasoningTier.ANALOGICAL
        assert len(result.causal_trace) == 1
        assert result.kg_paths_used == 1
        assert result.latency_ms == 2500.0

    def test_to_dict_keys(self):
        """to_dict() returns a dict with expected top-level keys."""
        result = ARIAResult(
            answer={"x": 1},
            tier=ReasoningTier.FALLBACK,
            confidence=0.3,
            reasoning_type="baseline_llm",
        )
        d = result.to_dict()
        assert "answer" in d
        assert "tier" in d
        assert "confidence" in d
        assert "reasoning_type" in d
        assert "causal_trace" in d
        assert "missing_evidence" in d
        assert "kg_paths_used" in d
        assert "kg_paths" in d
        assert "literature_papers" in d
        assert "source_attribution" in d
        assert "mode" in d
        assert "model" in d
        assert "latency_ms" in d

    def test_to_dict_enum_serialisation(self):
        """to_dict() serialises the tier enum as its integer value."""
        result = ARIAResult(
            answer={}, tier=ReasoningTier.DIRECT, confidence=0.9,
            reasoning_type="direct_path",
        )
        d = result.to_dict()
        assert d["tier"] == 1  # ReasoningTier.DIRECT.value

    def test_to_dict_with_causal_trace(self):
        """to_dict() serialises CausalTraceStep objects within causal_trace."""
        step = CausalTraceStep(processing="P", structure="S", property_="Q")
        result = ARIAResult(
            answer={}, tier=ReasoningTier.DIRECT, confidence=0.9,
            reasoning_type="direct_path", causal_trace=[step],
        )
        d = result.to_dict()
        assert isinstance(d["causal_trace"], list)
        assert len(d["causal_trace"]) == 1
        assert d["causal_trace"][0]["processing"] == "P"

    def test_to_dict_chain_of_thought(self):
        """to_dict() includes chain_of_thought when present."""
        cot = ChainOfThought(
            tier=1,
            kg_paths_used=2,
            literature_papers_used=0,
        )
        result = ARIAResult(
            answer={}, tier=ReasoningTier.DIRECT, confidence=0.9,
            reasoning_type="direct_path", chain_of_thought=cot,
        )
        d = result.to_dict()
        assert "chain_of_thought" in d
        assert d["chain_of_thought"]["tier"] == 1

    def test_to_dict_without_chain_of_thought(self):
        """to_dict() omits chain_of_thought when it is None."""
        result = ARIAResult(
            answer={}, tier=ReasoningTier.DIRECT, confidence=0.9,
            reasoning_type="direct_path",
        )
        d = result.to_dict()
        assert "chain_of_thought" not in d

    def test_to_json(self):
        """to_json() returns valid JSON string."""
        result = ARIAResult(
            answer={"mobility": "50"},
            tier=ReasoningTier.DIRECT,
            confidence=0.9,
            reasoning_type="direct_path",
        )
        json_str = result.to_json()
        assert isinstance(json_str, str)
        import json
        parsed = json.loads(json_str)
        assert parsed["confidence"] == 0.9


# ==========================================================================
# Enums
# ==========================================================================


class TestReasoningTier:
    """Tests for the ReasoningTier enum."""

    def test_values(self):
        """ReasoningTier has three tiers with expected integer values."""
        assert ReasoningTier.DIRECT.value == 1
        assert ReasoningTier.ANALOGICAL.value == 2
        assert ReasoningTier.FALLBACK.value == 3

    def test_from_value(self):
        """ReasoningTier can be constructed from integer values."""
        assert ReasoningTier(1) == ReasoningTier.DIRECT
        assert ReasoningTier(2) == ReasoningTier.ANALOGICAL
        assert ReasoningTier(3) == ReasoningTier.FALLBACK

    def test_iteration(self):
        """All three tiers are iterable."""
        tiers = list(ReasoningTier)
        assert len(tiers) == 3


class TestEngineMode:
    """Tests for the EngineMode enum."""

    def test_values(self):
        """EngineMode has five modes with expected string values."""
        assert EngineMode.BASELINE.value == "baseline"
        assert EngineMode.NAIVE_KG.value == "naive_kg"
        assert EngineMode.ARIA.value == "aria"
        assert EngineMode.ARIA_SEARCH.value == "aria_search"
        assert EngineMode.ARIA_FULL.value == "aria_full"

    def test_from_string(self):
        """EngineMode can be constructed from string values."""
        assert EngineMode("baseline") == EngineMode.BASELINE
        assert EngineMode("aria") == EngineMode.ARIA

    def test_invalid_mode_raises(self):
        """Constructing an invalid EngineMode raises ValueError."""
        with pytest.raises(ValueError):
            EngineMode("nonexistent_mode")


class TestPSPType:
    """Tests for the PSPType enum."""

    def test_values(self):
        """PSPType has the expected edge-type values."""
        assert PSPType.PROCESSING_TO_STRUCTURE.value == "Processing_to_Structure"
        assert PSPType.STRUCTURE_TO_PROPERTY.value == "Structure_to_Property"
        assert PSPType.PROCESSING_TO_PROPERTY.value == "Processing_to_Property"
        assert PSPType.STRUCTURE_TO_STRUCTURE.value == "Structure_to_Structure"
        assert PSPType.PROCESSING_TO_PROCESSING.value == "Processing_to_Processing"


# ==========================================================================
# Inference helpers
# ==========================================================================


class TestInferRelation:
    """Tests for _infer_relation()."""

    def test_increases_synonyms(self):
        """All 'increases' synonyms map to 'increases'."""
        for text in ["increases X", "improves Y", "enhances Z", "promotes W", "raises T"]:
            assert _infer_relation(text) == "increases"

    def test_decreases_synonyms(self):
        """All 'decreases' synonyms map to 'decreases'."""
        for text in ["decreases X", "reduces Y", "suppresses Z", "lowers W", "diminishes T"]:
            assert _infer_relation(text) == "decreases"

    def test_induces_synonyms(self):
        """All 'induces' synonyms map to 'induces'."""
        for text in ["induces X", "causes Y", "leads to Z", "produces W", "creates T"]:
            assert _infer_relation(text) == "induces"

    def test_inhibits_synonyms(self):
        """All 'inhibits' synonyms map to 'inhibits'."""
        for text in ["inhibits X", "prevents Y", "blocks Z", "hinders W"]:
            assert _infer_relation(text) == "inhibits"

    def test_fallback_affects(self):
        """Unrecognised text maps to 'affects'."""
        assert _infer_relation("modulates something") == "affects"
        assert _infer_relation("unknown effect") == "affects"
        assert _infer_relation("") == "affects"

    def test_case_insensitive(self):
        """_infer_relation is case-insensitive."""
        assert _infer_relation("INCREASES CARRIER MOBILITY") == "increases"
        assert _infer_relation("Decreases Defects") == "decreases"


class TestInferPspType:
    """Tests for _infer_psp_type()."""

    def test_processing_to_structure(self):
        """Processing cause + Structure effect -> Processing_to_Structure."""
        result = _infer_psp_type("CVD temperature", "crystallinity")
        assert result == PSPType.PROCESSING_TO_STRUCTURE.value

    def test_structure_to_property(self):
        """Structure cause + Property effect -> Structure_to_Property."""
        result = _infer_psp_type("crystallinity", "carrier mobility")
        assert result == PSPType.STRUCTURE_TO_PROPERTY.value

    def test_processing_to_property(self):
        """Processing cause + Property effect -> Processing_to_Property."""
        result = _infer_psp_type("doping concentration", "conductivity")
        assert result == PSPType.PROCESSING_TO_PROPERTY.value

    def test_structure_to_structure(self):
        """Structure cause + Structure effect -> Structure_to_Structure."""
        result = _infer_psp_type("grain size", "defect density")
        assert result == PSPType.STRUCTURE_TO_STRUCTURE.value

    def test_processing_default(self):
        """Processing cause + unrecognised effect -> Processing_to_Structure default."""
        result = _infer_psp_type("temperature", "unknown_effect")
        assert result == PSPType.PROCESSING_TO_STRUCTURE.value

    def test_fallback_default(self):
        """Neither recognised -> Processing_to_Property default."""
        result = _infer_psp_type("something_vague", "also_vague")
        assert result == PSPType.PROCESSING_TO_PROPERTY.value


class TestParseConfidence:
    """Tests for _parse_confidence()."""

    def test_experimentally_verified(self):
        assert _parse_confidence("experimentally proven") == 0.95
        assert _parse_confidence("proven by direct measurement") == 0.95

    def test_high_confidence(self):
        assert _parse_confidence("high confidence") == 0.85
        assert _parse_confidence("strong evidence") == 0.85

    def test_moderate_confidence(self):
        assert _parse_confidence("moderate") == 0.7
        assert _parse_confidence("medium confidence") == 0.7

    def test_low_confidence(self):
        assert _parse_confidence("low") == 0.5
        assert _parse_confidence("weak evidence") == 0.5

    def test_theoretical(self):
        assert _parse_confidence("theoretical prediction") == 0.6
        assert _parse_confidence("predicted by DFT") == 0.6

    def test_default(self):
        """Empty or unrecognised string returns 0.7."""
        assert _parse_confidence("") == 0.7
        assert _parse_confidence("unknown") == 0.7
        assert _parse_confidence("some random text") == 0.7


class TestInferMaterial:
    """Tests for _infer_material()."""

    def test_known_materials(self):
        """Known TMD material names are inferred from source_file.

        Materials with names <=4 chars are uppercased; longer names
        keep their original casing from the _infer_material lookup.
        """
        assert _infer_material("mos2_cvddoping.json") == "MOS2"
        assert _infer_material("ws2_growth.json") == "WS2"
        assert _infer_material("wse2_synthesis.json") == "WSE2"
        assert _infer_material("mose2_data.json") == "mose2"   # 5 chars, not uppercased
        assert _infer_material("mote2_results.json") == "mote2"  # 5 chars
        assert _infer_material("wte2_experiments.json") == "WTE2"

    def test_graphene(self):
        assert _infer_material("graphene_growth.json") == "graphene"

    def test_empty_string(self):
        assert _infer_material("") == ""

    def test_unknown_file(self):
        """Files without a known material name return empty string."""
        assert _infer_material("generic_data.json") == ""


# ==========================================================================
# Supporting dataclasses
# ==========================================================================


class TestKnowledgeSource:
    """Tests for the KnowledgeSource dataclass."""

    def test_creation(self):
        ks = KnowledgeSource(
            source_id="kg_1",
            content="MoS2 CVD temperature",
            source_type="kg_node",
            confidence=0.9,
            context="Knowledge graph node",
        )
        assert ks.source_id == "kg_1"
        assert ks.confidence == 0.9

    def test_to_dict(self):
        ks = KnowledgeSource(
            source_id="lit_1",
            content="Test",
            source_type="literature",
            confidence=0.8,
            context="Paper context",
        )
        d = ks.to_dict()
        assert d["source_id"] == "lit_1"
        assert d["source_type"] == "literature"


class TestReasoningStep:
    """Tests for the ReasoningStep dataclass."""

    def test_creation(self):
        step = ReasoningStep(
            step_id="step_1",
            description="Retrieved paths",
            reasoning_type="retrieval",
            confidence=0.9,
        )
        assert step.step_id == "step_1"
        assert step.evidence_sources == []

    def test_to_dict(self):
        step = ReasoningStep(
            step_id="step_1",
            description="Test step",
            reasoning_type="synthesis",
            confidence=0.7,
            intermediate_conclusion="Some conclusion",
        )
        d = step.to_dict()
        assert d["step_id"] == "step_1"
        assert d["confidence"] == 0.7
        assert d["evidence_sources"] == []


class TestChainOfThought:
    """Tests for the ChainOfThought dataclass."""

    def test_creation_defaults(self):
        cot = ChainOfThought()
        assert cot.reasoning_steps == []
        assert cot.final_reasoning == ""
        assert cot.tier == 0

    def test_to_dict(self):
        cot = ChainOfThought(tier=2, kg_paths_used=3, literature_papers_used=1)
        d = cot.to_dict()
        assert d["tier"] == 2
        assert d["kg_paths_used"] == 3
        assert d["literature_papers_used"] == 1