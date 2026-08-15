"""Tests for aria.engine_factory."""

import pytest

from aria.engine_factory import parse_kv_pairs, resolve_kg_path


def test_resolve_kg_path_returns_explicit_path(tmp_path):
    kg_file = tmp_path / "custom.json"
    kg_file.write_text("{}")
    assert resolve_kg_path(str(kg_file)) == str(kg_file)


def test_resolve_kg_path_raises_for_missing_explicit_path():
    with pytest.raises(FileNotFoundError):
        resolve_kg_path("/nonexistent/path/to/kg.json")


def test_resolve_kg_path_defaults_to_bundled_demo_kg():
    path = resolve_kg_path(None)
    assert path.endswith("aria_2d_kg_demo.json")
    from pathlib import Path
    assert Path(path).is_file()


def test_parse_kv_pairs_empty():
    assert parse_kv_pairs(None) == {}
    assert parse_kv_pairs([]) == {}


def test_parse_kv_pairs_basic():
    result = parse_kv_pairs(["temperature=750C", "method=CVD"])
    assert result == {"temperature": "750C", "method": "CVD"}


def test_parse_kv_pairs_strips_whitespace():
    result = parse_kv_pairs([" temperature = 750C "])
    assert result == {"temperature": "750C"}


def test_parse_kv_pairs_rejects_missing_equals():
    with pytest.raises(ValueError, match="key=value"):
        parse_kv_pairs(["not-a-pair"])


def test_parse_kv_pairs_rejects_empty_key():
    with pytest.raises(ValueError, match="empty key"):
        parse_kv_pairs(["=value"])


from aria.engine import ARIAEngine
from aria.engine_factory import OllamaUnavailableError, build_engine


def test_build_engine_rejects_unknown_mode(tmp_path):
    kg_file = tmp_path / "kg.json"
    kg_file.write_text('{"directed": true, "nodes": [], "links": []}')
    with pytest.raises(ValueError, match="Unknown mode"):
        build_engine(str(kg_file), mode="not_a_real_mode")


def test_build_engine_raises_when_ollama_unreachable(tmp_path, monkeypatch):
    kg_file = tmp_path / "kg.json"
    kg_file.write_text('{"directed": true, "nodes": [], "links": []}')

    def fake_urlopen(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("aria.engine_factory.urlopen", fake_urlopen)

    with pytest.raises(OllamaUnavailableError, match="ollama serve"):
        build_engine(str(kg_file), mode="baseline")


@pytest.mark.slow
def test_build_engine_returns_engine_when_ollama_reachable():
    """Requires a live Ollama server with qwen2:7b pulled."""
    from aria.engine_factory import resolve_kg_path

    engine = build_engine(resolve_kg_path(None), mode="aria")
    assert isinstance(engine, ARIAEngine)
