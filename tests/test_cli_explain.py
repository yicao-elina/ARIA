"""Tests for `aria explain`."""

import pytest
from typer.testing import CliRunner

from aria.cli.app import app

runner = CliRunner()


def test_explain_rejects_bad_direction():
    result = runner.invoke(
        app,
        ["explain", "--direction", "sideways", "--target-property", "carrier mobility"],
    )
    assert result.exit_code == 1
    assert "must be 'forward' or 'inverse'" in result.stdout


def test_explain_forward_requires_material():
    result = runner.invoke(
        app,
        ["explain", "--direction", "forward", "--target-property", "carrier mobility"],
    )
    assert result.exit_code == 1
    assert "--material" in result.stdout


def test_explain_inverse_requires_target_material():
    result = runner.invoke(
        app,
        ["explain", "--direction", "inverse", "--target-property", "carrier mobility"],
    )
    assert result.exit_code == 1
    assert "--target-material" in result.stdout


def test_explain_rejects_missing_kg_file():
    result = runner.invoke(
        app,
        [
            "explain", "--direction", "forward", "--material", "MoS2",
            "--target-property", "carrier mobility", "--kg", "/nonexistent/kg.json",
        ],
    )
    assert result.exit_code == 1
    assert "KG file not found" in result.stdout


@pytest.mark.slow
def test_explain_forward_happy_path():
    """Requires a live Ollama server with qwen2:7b pulled."""
    result = runner.invoke(
        app,
        [
            "explain", "--direction", "forward", "--material", "MoS2",
            "--target-property", "carrier mobility", "--temperature", "750C", "--method", "CVD",
        ],
    )
    assert result.exit_code == 0
    assert "Chain of thought" in result.stdout or "No chain-of-thought available" in result.stdout
