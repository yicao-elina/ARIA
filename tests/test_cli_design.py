"""Tests for `aria design`."""

import pytest
from typer.testing import CliRunner

from aria.cli.app import app

runner = CliRunner()


def test_design_rejects_unknown_mode():
    result = runner.invoke(
        app,
        [
            "design", "--target-material", "MoS2", "--target-property", "high n-type mobility",
            "--mode", "not_a_real_mode",
        ],
    )
    assert result.exit_code == 1
    assert "Unknown mode" in result.stdout


def test_design_rejects_missing_kg_file():
    result = runner.invoke(
        app,
        [
            "design", "--target-material", "MoS2", "--target-property", "high n-type mobility",
            "--kg", "/nonexistent/kg.json",
        ],
    )
    assert result.exit_code == 1
    assert "KG file not found" in result.stdout


@pytest.mark.slow
def test_design_happy_path_json_output():
    """Requires a live Ollama server with qwen2:7b pulled."""
    result = runner.invoke(
        app,
        [
            "design", "--target-material", "MoS2", "--target-property", "high n-type mobility",
            "--method", "CVD", "--json",
        ],
    )
    assert result.exit_code == 0
    assert '"tier"' in result.stdout
