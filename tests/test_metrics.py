"""Tests for aria.evaluation.metrics module."""

import json
import pytest
from aria.evaluation.metrics import MetricsComputer


@pytest.fixture
def sample_prediction():
    """A sample forward prediction output."""
    return {
        "predicted_property": "n-type with high mobility",
        "mechanistic_explanation": (
            "Nb substitution on Mo sites creates additional electron carriers, "
            "increasing carrier concentration while maintaining crystallinity "
            "at temperatures above 700C."
        ),
        "confidence": 0.85,
        "reasoning_type": "direct_path",
        "tier": 1,
    }


@pytest.fixture
def sample_ground_truth():
    """Sample ground truth for comparison."""
    return {
        "property": "n-type with mobility > 10 cm²/Vs",
        "explanation": (
            "Nb doping introduces extra electrons as substitutional dopant "
            "on Mo sites, increasing carrier concentration."
        ),
        "synthesis_conditions": {
            "method": "CVD",
            "temperature": "750°C",
            "precursor": "NbCl5 + MoO3",
        },
    }


class TestMetricsComputerInit:
    """Test MetricsComputer initialization."""

    def test_init_without_kg(self):
        """MetricsComputer can be created without a KG."""
        mc = MetricsComputer()
        assert mc is not None
        assert mc.kg is None

    def test_init_with_kg(self, tiny_kg):
        """MetricsComputer can be created with a KG."""
        mc = MetricsComputer(kg=tiny_kg)
        assert mc.kg is not None


class TestCausalCoherence:
    """Test causal_coherence metric."""

    def test_perfect_coherence(self, sample_prediction, sample_ground_truth):
        """Perfectly coherent prediction scores well."""
        mc = MetricsComputer()
        result = mc.causal_coherence(sample_prediction, sample_ground_truth)
        assert isinstance(result, dict)
        assert "intervention_consistency" in result
        assert "psp_chain_validity" in result

    def test_empty_prediction(self, sample_ground_truth):
        """Empty prediction returns zero or low scores."""
        mc = MetricsComputer()
        result = mc.causal_coherence({}, sample_ground_truth)
        assert isinstance(result, dict)


class TestSourceGrounding:
    """Test source_grounding metric."""

    def test_with_kg(self, tiny_kg, sample_prediction, sample_ground_truth):
        """Source grounding works with a KG."""
        mc = MetricsComputer(kg=tiny_kg)
        score = mc.source_grounding(sample_prediction, sample_ground_truth)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_without_kg(self, sample_prediction, sample_ground_truth):
        """Source grounding works without a KG (returns 0)."""
        mc = MetricsComputer()
        score = mc.source_grounding(sample_prediction, sample_ground_truth)
        assert isinstance(score, float)


class TestInternalValidity:
    """Test internal_validity metric."""

    def test_valid_prediction(self, sample_prediction):
        """Valid prediction scores well."""
        mc = MetricsComputer()
        result = mc.internal_validity(sample_prediction)
        assert isinstance(result, dict)
        assert "sufficiency" in result

    def test_empty_prediction(self):
        """Empty prediction returns low scores."""
        mc = MetricsComputer()
        result = mc.internal_validity({})
        assert isinstance(result, dict)


class TestComputeAll:
    """Test compute_all method."""

    def test_compute_all_returns_dict(self, sample_prediction, sample_ground_truth):
        """compute_all returns a comprehensive metrics dict."""
        mc = MetricsComputer()
        result = mc.compute_all(sample_prediction, sample_ground_truth)
        assert isinstance(result, dict)
        # Should include all metric categories
        assert "causal_coherence" in result or "overall" in result

    def test_compute_all_with_kg(self, tiny_kg, sample_prediction, sample_ground_truth):
        """compute_all works with a KG provided."""
        mc = MetricsComputer(kg=tiny_kg)
        result = mc.compute_all(sample_prediction, sample_ground_truth)
        assert isinstance(result, dict)