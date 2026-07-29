"""Tests for the aria-mcp server."""

import pytest

from aria.mcp.server import mcp


def test_mcp_server_is_named_aria():
    assert mcp.name == "aria"


from aria.mcp.server import predict


def test_predict_tool_returns_error_dict_for_unknown_mode():
    result = predict(
        material="MoS2",
        target_property="carrier mobility",
        mode="not_a_real_mode",
    )
    assert "error" in result
    assert "Unknown mode" in result["error"]


def test_predict_tool_returns_error_dict_for_missing_kg():
    result = predict(
        material="MoS2",
        target_property="carrier mobility",
        kg="/nonexistent/kg.json",
    )
    assert "error" in result
    assert "KG file not found" in result["error"]


from aria.mcp.server import design


def test_design_tool_returns_error_dict_for_unknown_mode():
    result = design(
        target_material="MoS2",
        target_property="high n-type mobility",
        mode="not_a_real_mode",
    )
    assert "error" in result
    assert "Unknown mode" in result["error"]


def test_design_tool_returns_error_dict_for_missing_kg():
    result = design(
        target_material="MoS2",
        target_property="high n-type mobility",
        kg="/nonexistent/kg.json",
    )
    assert "error" in result
    assert "KG file not found" in result["error"]


from aria.mcp.server import explain


def test_explain_tool_rejects_bad_direction():
    result = explain(direction="sideways", target_property="carrier mobility")
    assert "error" in result
    assert "direction" in result["error"]


def test_explain_tool_forward_requires_material():
    result = explain(direction="forward", target_property="carrier mobility")
    assert "error" in result
    assert "material" in result["error"]


def test_explain_tool_inverse_requires_target_material():
    result = explain(direction="inverse", target_property="carrier mobility")
    assert "error" in result
    assert "target_material" in result["error"]


from aria.mcp.server import diagnose


def test_diagnose_tool_returns_error_dict_for_missing_kg():
    result = diagnose(kg="/nonexistent/kg.json")
    assert "error" in result
    assert "KG file not found" in result["error"]


@pytest.mark.slow
def test_diagnose_tool_happy_path_on_bundled_tiny_kg():
    """Loads a sentence-transformers model for diversity analysis."""
    import importlib.resources

    tiny_kg = str(importlib.resources.files("aria.data").joinpath("aria_2d_kg_tiny.json"))
    result = diagnose(kg=tiny_kg)
    assert "structure" in result
    assert "gaps" in result
