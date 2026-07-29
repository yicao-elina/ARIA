"""Tests for `aria diagnose`."""

import pytest
from typer.testing import CliRunner

from aria.cli.app import app

runner = CliRunner()


def test_diagnose_rejects_missing_kg_file():
    result = runner.invoke(app, ["diagnose", "--kg", "/nonexistent/kg.json"])
    assert result.exit_code == 1
    assert "KG file not found" in result.stdout


@pytest.mark.slow
def test_diagnose_happy_path_on_bundled_tiny_kg():
    """Loads a sentence-transformers model for diversity analysis."""
    import importlib.resources

    tiny_kg = str(importlib.resources.files("aria.data").joinpath("aria_2d_kg_tiny.json"))
    result = runner.invoke(app, ["diagnose", "--kg", tiny_kg])
    assert result.exit_code == 0
    assert "KNOWLEDGE GRAPH QUALITY DIAGNOSTIC REPORT" in result.stdout


@pytest.mark.slow
def test_diagnose_saves_json_report(tmp_path):
    import importlib.resources

    tiny_kg = str(importlib.resources.files("aria.data").joinpath("aria_2d_kg_tiny.json"))
    out_file = tmp_path / "report.json"
    result = runner.invoke(app, ["diagnose", "--kg", tiny_kg, "--save-json", str(out_file)])
    assert result.exit_code == 0
    assert out_file.is_file()
