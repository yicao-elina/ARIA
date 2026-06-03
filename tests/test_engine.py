"""
Tests for aria.engine -- ARIAEngine initialisation, forward_predict,
inverse_design, mode switching, and diagnose_kg.

All LLM calls are mocked so the tests run without Ollama or any
LLM service. Tests that genuinely require an LLM are marked with
pytest.mark.skip.
"""

import json
from unittest.mock import MagicMock, patch, PropertyMock

import networkx as nx
import pytest

from aria.types import ARIAResult, EngineMode, ReasoningTier


# ==========================================================================
# Helper: create a mock LLM client
# ==========================================================================


def _mock_llm_client():
    """Create a mock LLM client that returns plausible responses."""
    client = MagicMock()

    # Default forward-prediction response
    client.generate_json.return_value = {
        "predicted_properties": {
            "carrier_type": "n-type",
            "mobility": "45 cm2/Vs",
            "conductivity": "moderate",
        },
        "mechanistic_explanation": {
            "primary_mechanism": "CVD temperature improves crystallinity",
            "chain_of_thought": ["High temp -> crystal growth -> better transport"],
        },
        "confidence": 0.85,
        "reasoning": "Based on direct KG path evidence",
        "tier": 1,
        "reasoning_type": "direct_path",
    }

    return client


def _mock_llm_inverse_response():
    """Return a plausible inverse-design response dict."""
    return {
        "suggested_synthesis_conditions": {
            "method": "CVD",
            "temperature_c": 750,
            "pressure_pa": 101325,
        },
        "mechanistic_explanation": {
            "primary_mechanism": "CVD at 750C yields optimal crystallinity",
            "chain_of_thought": ["Target -> property -> structure -> processing"],
        },
        "confidence": 0.78,
        "reasoning": "Inverse path found in KG",
        "tier": 1,
        "reasoning_type": "direct_inverse",
    }


def _create_engine_with_mock_llm(kg=None, mode="aria", **kwargs):
    """Create an ARIAEngine with a mock LLM client, bypassing Ollama.

    This patches ``_create_llm_client`` to return a MagicMock, and
    ``NodeMatcher`` to avoid needing sentence-transformers.
    """
    from aria.engine import ARIAEngine

    mock_llm = _mock_llm_client()

    with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
        with patch("aria.engine.NodeMatcher") as MockMatcher:
            mock_matcher_instance = MagicMock()
            MockMatcher.return_value = mock_matcher_instance
            if kg is not None or mode == "baseline":
                if kg is not None:
                    engine = ARIAEngine(kg=kg, mode=mode, **kwargs)
                else:
                    engine = ARIAEngine(mode=mode, **kwargs)
            else:
                raise ValueError("Non-baseline mode requires a KG")

    # Ensure the LLM is the mock
    engine.llm = mock_llm
    return engine


# ==========================================================================
# ARIAEngine initialisation
# ==========================================================================


class TestARIAEngineInit:
    """Tests for ARIAEngine initialisation."""

    def test_init_with_kg(self, tiny_kg):
        """ARIAEngine can be initialised with a pre-loaded KG (LLM mocked)."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            with patch("aria.engine.NodeMatcher"):
                engine = ARIAEngine(kg=tiny_kg, mode="aria")
        assert engine.kg is tiny_kg
        assert engine.mode == EngineMode.ARIA

    def test_init_baseline_mode_no_kg(self):
        """Baseline mode works without a KG (LLM mocked)."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            engine = ARIAEngine(mode="baseline")
        assert engine.kg is None
        assert engine.mode == EngineMode.BASELINE

    def test_init_requires_kg_for_aria_mode(self):
        """ARIA mode raises ValueError when no KG is provided."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            with pytest.raises(ValueError, match="requires a knowledge graph"):
                ARIAEngine(mode="aria")

    def test_init_requires_kg_for_naive_kg_mode(self):
        """Naive KG mode raises ValueError when no KG is provided."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            with pytest.raises(ValueError, match="requires a knowledge graph"):
                ARIAEngine(mode="naive_kg")

    def test_init_sets_model_name(self, tiny_kg):
        """The model name is stored correctly."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            with patch("aria.engine.NodeMatcher"):
                engine = ARIAEngine(kg=tiny_kg, model="test-model", mode="aria")
        assert engine.model == "test-model"

    def test_init_invalid_mode(self, tiny_kg):
        """An invalid mode string raises ValueError."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            with pytest.raises(ValueError):
                ARIAEngine(kg=tiny_kg, mode="nonexistent_mode")


# ==========================================================================
# ARIAEngine: mode switching
# ==========================================================================


class TestEngineModeSwitching:
    """Tests for switching between ARIA engine modes."""

    @pytest.mark.parametrize("mode_str", ["baseline", "naive_kg", "aria", "aria_search", "aria_full"])
    def test_mode_creation(self, mode_str, tiny_kg):
        """Each mode string creates the correct EngineMode."""
        engine_mode = EngineMode(mode_str)
        assert engine_mode.value == mode_str

    def test_baseline_mode(self):
        """Baseline mode stores None KG and correct mode."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            engine = ARIAEngine(mode="baseline")
        assert engine.mode == EngineMode.BASELINE
        assert engine.kg is None


# ==========================================================================
# ARIAEngine: diagnose_kg
# ==========================================================================


class TestDiagnoseKg:
    """Tests for ARIAEngine.diagnose_kg()."""

    def test_diagnose_with_kg(self, tiny_kg):
        """diagnose_kg() returns stats dict when KG is loaded."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            with patch("aria.engine.NodeMatcher"):
                engine = ARIAEngine(kg=tiny_kg, mode="aria")

        stats = engine.diagnose_kg()
        assert isinstance(stats, dict)
        assert "num_nodes" in stats
        assert "num_edges" in stats
        assert stats["num_nodes"] == tiny_kg.number_of_nodes()
        assert stats["num_edges"] == tiny_kg.number_of_edges()

    def test_diagnose_without_kg(self):
        """diagnose_kg() returns a status message when no KG is loaded."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            engine = ARIAEngine(mode="baseline")

        result = engine.diagnose_kg()
        assert isinstance(result, dict)
        assert "status" in result
        assert "No KG loaded" in result["status"]


# ==========================================================================
# ARIAEngine: forward_predict (mocked LLM)
# ==========================================================================


class TestForwardPredict:
    """Tests for ARIAEngine.forward_predict() with mocked LLM."""

    def test_forward_returns_aria_result(self, tiny_kg):
        """forward_predict() returns an ARIAResult object."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            with patch("aria.engine.NodeMatcher"):
                engine = ARIAEngine(kg=tiny_kg, mode="aria")
                engine.matcher = MagicMock()
                engine.matcher.precompute = MagicMock()

                # Patch router to force Tier 1 (direct path)
                engine.router = MagicMock()
                engine.router.route_forward.return_value = MagicMock(
                    tier=ReasoningTier.DIRECT,
                    paths=["CVD temperature 750C -> improved crystallinity -> higher carrier mobility"],
                    mechanisms=["Thermal activation of carriers"],
                    similar_node=None,
                    similarity=0.0,
                )

                # Patch tier1 reasoner
                engine.tier1 = MagicMock()
                engine.tier1.forward.return_value = {
                    "predicted_properties": {"mobility": "50 cm2/Vs"},
                    "confidence": 0.85,
                    "tier": 1,
                    "reasoning_type": "direct_path",
                    "kg_paths_used": 1,
                    "mechanistic_explanation": {"primary_mechanism": "test"},
                }

                result = engine.forward_predict(
                    material="MoS2",
                    processing={"temperature": "750C", "method": "CVD"},
                    target_property="carrier mobility",
                )

        assert isinstance(result, ARIAResult)
        assert result.tier == ReasoningTier.DIRECT
        assert result.confidence > 0

    def test_forward_baseline_mode(self):
        """Baseline mode returns an ARIAResult even without KG."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            engine = ARIAEngine(mode="baseline")

            # Patch tier3 to return a response
            engine.tier3 = MagicMock()
            engine.tier3.forward.return_value = {
                "predicted_properties": {"mobility": "40 cm2/Vs"},
                "confidence": 0.5,
                "tier": 3,
                "reasoning_type": "baseline_llm",
                "kg_paths_used": 0,
            }

            result = engine.forward_predict(
                material="MoS2",
                processing={"temperature": "750C"},
            )

        assert isinstance(result, ARIAResult)
        assert result.mode == "baseline"

    def test_forward_naive_kg_mode(self, tiny_kg):
        """Naive KG mode returns an ARIAResult with mocked LLM."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        mock_llm.generate_json.return_value = {
            "predicted_properties": {"mobility": "45 cm2/Vs"},
            "confidence": 0.7,
            "tier": 1,
            "reasoning_type": "naive_kg",
            "kg_paths_used": 1,
        }

        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            with patch("aria.engine.NodeMatcher"):
                engine = ARIAEngine(kg=tiny_kg, mode="naive_kg")
                engine.matcher = MagicMock()
                engine.matcher.precompute = MagicMock()
                # The naive mode calls LLM directly; mock is already set
                engine.llm = mock_llm

                result = engine.forward_predict(
                    material="MoS2",
                    processing={"temperature": "750C", "method": "CVD"},
                )

        assert isinstance(result, ARIAResult)
        assert result.mode == "naive_kg"


# ==========================================================================
# ARIAEngine: inverse_design (mocked LLM)
# ==========================================================================


class TestInverseDesign:
    """Tests for ARIAEngine.inverse_design() with mocked LLM."""

    def test_inverse_returns_aria_result(self, tiny_kg):
        """inverse_design() returns an ARIAResult object."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        mock_llm.generate_json.return_value = _mock_llm_inverse_response()

        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            with patch("aria.engine.NodeMatcher"):
                engine = ARIAEngine(kg=tiny_kg, mode="aria")
                engine.matcher = MagicMock()
                engine.matcher.precompute = MagicMock()

                # Patch router for Tier 1
                engine.router = MagicMock()
                engine.router.route_inverse.return_value = MagicMock(
                    tier=ReasoningTier.DIRECT,
                    paths=["CVD temperature 750C -> improved crystallinity"],
                    mechanisms=["Thermal activation"],
                    similar_node=None,
                    similarity=0.0,
                )

                # Patch tier1
                engine.tier1 = MagicMock()
                engine.tier1.inverse.return_value = {
                    "suggested_synthesis_conditions": {"method": "CVD", "temperature_c": 750},
                    "confidence": 0.78,
                    "tier": 1,
                    "reasoning_type": "direct_inverse",
                    "kg_paths_used": 1,
                }

                result = engine.inverse_design(
                    target_material="MoS2",
                    target_property="high n-type mobility",
                )

        assert isinstance(result, ARIAResult)

    def test_inverse_baseline_mode(self):
        """Baseline inverse design returns ARIAResult without KG."""
        from aria.engine import ARIAEngine

        mock_llm = _mock_llm_client()
        mock_llm.generate_json.return_value = _mock_llm_inverse_response()

        with patch.object(ARIAEngine, "_create_llm_client", return_value=mock_llm):
            engine = ARIAEngine(mode="baseline")

            engine.tier3 = MagicMock()
            engine.tier3.inverse.return_value = {
                "suggested_synthesis_conditions": {"method": "CVD"},
                "confidence": 0.5,
                "tier": 3,
                "reasoning_type": "baseline_llm_inverse",
                "kg_paths_used": 0,
            }

            result = engine.inverse_design(
                target_material="MoS2",
                target_property="high mobility",
            )

        assert isinstance(result, ARIAResult)
        assert result.mode == "baseline"


# ==========================================================================
# ARIAEngine: internal helpers
# ==========================================================================


class TestEngineHelpers:
    """Tests for ARIAEngine internal helper methods."""

    def test_extract_keywords(self):
        """_extract_keywords() converts dict values to a list of strings."""
        from aria.engine import ARIAEngine

        keywords = ARIAEngine._extract_keywords(
            {"method": "CVD", "temperature": 750, "material": "MoS2"}
        )
        assert "CVD" in keywords
        assert "750" in keywords
        assert "MoS2" in keywords
        assert len(keywords) == 3

    def test_extract_keywords_handles_none(self):
        """_extract_keywords() skips None values."""
        from aria.engine import ARIAEngine

        keywords = ARIAEngine._extract_keywords(
            {"method": "CVD", "temperature": None}
        )
        assert len(keywords) == 1
        assert "CVD" in keywords

    def test_format_literature_context_empty(self):
        """_format_literature_context() handles empty results."""
        from aria.engine import ARIAEngine

        result = ARIAEngine._format_literature_context([])
        assert "No relevant literature" in result

    def test_format_literature_context_with_results(self):
        """_format_literature_context() formats paper details."""
        from aria.engine import ARIAEngine

        papers = [
            {
                "title": "Test Paper on MoS2",
                "authors": ["Author A", "Author B"],
                "year": 2024,
                "citations": 42,
                "abstract": "A short abstract for testing purposes.",
                "source": "OpenAlex",
            }
        ]
        result = ARIAEngine._format_literature_context(papers)
        assert "Test Paper on MoS2" in result
        assert "Author A" in result
        assert "42" in result


# ==========================================================================
# ARIAEngine: requires Ollama (skipped)
# ==========================================================================


class TestRequiresOllama:
    """Tests that genuinely require an Ollama server running.

    These tests are marked with pytest.mark.skip and serve as
    documentation for integration testing.
    """

    @pytest.mark.skip(reason="Requires running Ollama server")
    def test_forward_with_real_llm(self, tiny_kg):
        """Integration test: forward_predict with a real LLM (requires Ollama)."""
        from aria.engine import ARIAEngine

        engine = ARIAEngine(kg=tiny_kg, model="qwen2:7b", mode="aria")
        result = engine.forward_predict(
            material="MoS2",
            processing={"temperature": "750C", "method": "CVD"},
            target_property="carrier mobility",
        )
        assert isinstance(result, ARIAResult)

    @pytest.mark.skip(reason="Requires running Ollama server")
    def test_inverse_with_real_llm(self, tiny_kg):
        """Integration test: inverse_design with a real LLM (requires Ollama)."""
        from aria.engine import ARIAEngine

        engine = ARIAEngine(kg=tiny_kg, model="qwen2:7b", mode="aria")
        result = engine.inverse_design(
            target_material="MoS2",
            target_property="high n-type mobility",
        )
        assert isinstance(result, ARIAResult)

    @pytest.mark.skip(reason="Requires running Ollama server")
    def test_baseline_forward_with_real_llm(self):
        """Integration test: baseline forward with real LLM (requires Ollama)."""
        from aria.engine import ARIAEngine

        engine = ARIAEngine(mode="baseline", model="qwen2:7b")
        result = engine.forward_predict(
            material="MoS2",
            processing={"temperature": "750C"},
        )
        assert isinstance(result, ARIAResult)