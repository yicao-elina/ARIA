"""Packaging sanity checks: bundled data files and console-script entries."""

import importlib.resources
from pathlib import Path


def test_bundled_demo_kg_exists():
    path = importlib.resources.files("aria.data").joinpath("aria_2d_kg_demo.json")
    assert path.is_file()


def test_bundled_tiny_kg_exists():
    path = importlib.resources.files("aria.data").joinpath("aria_2d_kg_tiny.json")
    assert path.is_file()


def test_no_broken_diagnose_entry_point():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    content = pyproject.read_text()
    assert "aria-diagnose" not in content
