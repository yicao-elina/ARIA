# ARIA CLI + MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Typer-based `aria` CLI (`predict`/`design`/`explain`/`diagnose`) and a thin `aria-mcp` MCP server mirroring it, both wrapping the existing `ARIAEngine`, plus fix two packaging bugs found during investigation.

**Architecture:** A new `aria/engine_factory.py` module centralizes KG-path resolution, `key=value` parsing, and `ARIAEngine` construction (including a friendly error when Ollama is unreachable). `aria/cli/app.py` (Typer) and `aria/mcp/server.py` (FastMCP) each call only `engine_factory` + `ARIAEngine` — no reasoning logic lives in either presentation layer.

**Tech Stack:** Typer (CLI), the official `mcp` Python SDK / FastMCP (MCP server, stdio transport), pytest + Typer's `CliRunner` (tests).

## Global Constraints

- Design source: `docs/superpowers/specs/2026-07-26-cli-mcp-design.md` — read it if anything below is ambiguous.
- Scope: CLI + MCP code only. **Do not** publish to PyPI, **do not** implement `aria/llm/openai_client.py`. ARIA requires a local Ollama server — this is a documented limitation, not a bug to fix.
- CLI and MCP live as subpackages of the existing `aria-materials` package (`aria/cli/`, `aria/mcp/`), not a separate repo.
- The official `mcp` PyPI package requires Python **>=3.10** (confirmed via `pypi.org/pypi/mcp/json`, current release 1.28.1). Bumping `requires-python` from `>=3.9` to `>=3.10` for the whole package is part of this plan (Task 11) — call this out explicitly in that task's commit, don't bury it.
- Ruff config: line-length 100. Bump `target-version` from `"py39"` to `"py310"` alongside the `requires-python` bump (same task).
- Existing test convention (`tests/conftest.py`, `pyproject.toml` markers): mark any test that needs a live Ollama server or loads a `sentence-transformers` model with `@pytest.mark.slow`. Fast tests must not require either.
- No code in `aria/cli/` or `aria/mcp/` may contain reasoning/business logic — both call `aria.engine_factory` and `aria.engine.ARIAEngine`/`aria.kg.diagnostics.KGDiagnostics` only.
- All new Python files: full type hints, module docstring, consistent with existing style in `aria/engine.py` and `aria/types.py`.

---

### Task 1: Bundle demo/tiny KG data + remove broken `aria-diagnose` entry point

**Files:**
- Create: `aria/data/aria_2d_kg_demo.json` (copy of `data/aria_2d_kg_demo.json`)
- Create: `aria/data/aria_2d_kg_tiny.json` (copy of `data/aria_2d_kg_tiny.json`)
- Modify: `pyproject.toml:42` (remove the `aria-diagnose` line)
- Test: `tests/test_packaging.py`

**Interfaces:**
- Produces: `aria.data` package now contains `aria_2d_kg_demo.json` and `aria_2d_kg_tiny.json`, resolvable via `importlib.resources.files("aria.data")`. Task 2's `resolve_kg_path()` depends on this.

- [ ] **Step 1: Write the failing test**

Create `tests/test_packaging.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_packaging.py -v`
Expected: 3 FAILED (files don't exist yet; `aria-diagnose` still present in `pyproject.toml`)

- [ ] **Step 3: Bundle the data files and remove the broken entry point**

```bash
cp data/aria_2d_kg_demo.json aria/data/aria_2d_kg_demo.json
cp data/aria_2d_kg_tiny.json aria/data/aria_2d_kg_tiny.json
```

Edit `pyproject.toml` — remove line 42 (`aria-diagnose = "aria.kg.diagnostics:main"`) from the `[project.scripts]` table, so it reads:

```toml
[project.scripts]
aria-benchmark = "aria.evaluation.benchmark:main"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_packaging.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add aria/data/aria_2d_kg_demo.json aria/data/aria_2d_kg_tiny.json pyproject.toml tests/test_packaging.py
git commit -m "fix: bundle demo/tiny KG in aria/data, drop broken aria-diagnose entry point"
```

---

### Task 2: `engine_factory.py` — KG path resolution and key=value parsing

**Files:**
- Create: `aria/engine_factory.py`
- Test: `tests/test_engine_factory.py`

**Interfaces:**
- Consumes: `aria.data` package contents from Task 1.
- Produces: `resolve_kg_path(kg_arg: Optional[str] = None) -> str` and `parse_kv_pairs(pairs: Optional[List[str]]) -> Dict[str, str]`. Task 3 (`build_engine`) and all CLI/MCP tasks import both from `aria.engine_factory`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_factory.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_engine_factory.py -v`
Expected: FAILED with `ModuleNotFoundError: No module named 'aria.engine_factory'`

- [ ] **Step 3: Write minimal implementation**

Create `aria/engine_factory.py`:

```python
"""Shared helpers for building an ARIAEngine from CLI/MCP-style arguments.

Both `aria.cli` and `aria.mcp` call these functions so the two surfaces
cannot drift on KG resolution, argument parsing, or error messages.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Dict, List, Optional


def resolve_kg_path(kg_arg: Optional[str] = None) -> str:
    """Resolve a knowledge-graph file path.

    If *kg_arg* is given, it must point to an existing file and is
    returned unchanged. Otherwise, the bundled demo KG shipped inside
    ``aria/data`` is returned, so callers get a usable default with
    zero configuration.
    """
    if kg_arg is not None:
        if not Path(kg_arg).is_file():
            raise FileNotFoundError(f"KG file not found: {kg_arg}")
        return kg_arg

    demo_path = importlib.resources.files("aria.data").joinpath("aria_2d_kg_demo.json")
    return str(demo_path)


def parse_kv_pairs(pairs: Optional[List[str]]) -> Dict[str, str]:
    """Parse a list of ``key=value`` strings into a dict.

    Raises ``ValueError`` naming the offending entry if any item doesn't
    contain an ``=``, or has an empty key.
    """
    result: Dict[str, str] = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(
                f"Invalid key=value pair: {item!r} (expected format 'key=value')"
            )
        key, _, value = item.partition("=")
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid key=value pair: {item!r} (empty key)")
        result[key] = value.strip()
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_engine_factory.py -v`
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add aria/engine_factory.py tests/test_engine_factory.py
git commit -m "feat: add engine_factory KG path resolution and kv-pair parsing"
```

---

### Task 3: `engine_factory.py` — `build_engine()` with mode validation and Ollama check

**Files:**
- Modify: `aria/engine_factory.py`
- Modify: `tests/test_engine_factory.py`

**Interfaces:**
- Consumes: `aria.engine.ARIAEngine`, `aria.types.EngineMode`.
- Produces: `OllamaUnavailableError` (exception class) and `build_engine(kg_path: str, model: str = "qwen2:7b", mode: str = "aria", llm_backend: str = "ollama", llm_base_url: str = "http://localhost:11434") -> ARIAEngine`. Every CLI command and MCP tool that needs live inference calls this.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_engine_factory.py`:

```python
from aria.engine_factory import OllamaUnavailableError, build_engine
from aria.engine import ARIAEngine


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_engine_factory.py -v -k "not slow"`
Expected: 2 new tests FAILED with `ImportError`/`AttributeError` (`build_engine`, `OllamaUnavailableError` don't exist yet)

- [ ] **Step 3: Implement `build_engine`**

Modify `aria/engine_factory.py` — add these imports at the top (alongside the existing ones) and the new code at the bottom of the file:

```python
from urllib.error import URLError
from urllib.request import urlopen

from aria.engine import ARIAEngine
from aria.types import EngineMode
```

```python
class OllamaUnavailableError(RuntimeError):
    """Raised when the configured Ollama backend cannot be reached."""


def build_engine(
    kg_path: str,
    model: str = "qwen2:7b",
    mode: str = "aria",
    llm_backend: str = "ollama",
    llm_base_url: str = "http://localhost:11434",
) -> ARIAEngine:
    """Validate inputs and construct an `ARIAEngine`.

    Raises ``ValueError`` for an unknown *mode*, and
    ``OllamaUnavailableError`` if *llm_backend* is ``"ollama"`` and the
    server cannot be reached at *llm_base_url*.
    """
    valid_modes = {m.value for m in EngineMode}
    if mode not in valid_modes:
        raise ValueError(f"Unknown mode {mode!r}. Valid modes: {sorted(valid_modes)}")

    if llm_backend == "ollama":
        _check_ollama_reachable(llm_base_url)

    return ARIAEngine(
        kg_file=kg_path,
        model=model,
        mode=mode,
        llm_backend=llm_backend,
        llm_base_url=llm_base_url,
    )


def _check_ollama_reachable(base_url: str) -> None:
    """Raise `OllamaUnavailableError` with a concrete fix if Ollama is down."""
    try:
        urlopen(f"{base_url}/api/version", timeout=2)
    except (URLError, OSError) as exc:
        raise OllamaUnavailableError(
            f"Could not reach Ollama at {base_url} ({exc}). "
            "Start it with `ollama serve`, and make sure the model is "
            "pulled, e.g. `ollama pull qwen2:7b`."
        ) from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_engine_factory.py -v -k "not slow"`
Expected: 10 PASSED (the `@pytest.mark.slow` test is excluded by `-k "not slow"`; run it separately with Ollama running if you want to confirm the happy path)

- [ ] **Step 5: Commit**

```bash
git add aria/engine_factory.py tests/test_engine_factory.py
git commit -m "feat: add build_engine with mode validation and Ollama reachability check"
```

---

### Task 4: CLI scaffold — `aria/cli/app.py` base, `--version`, console script

**Files:**
- Create: `aria/cli/__init__.py`
- Create: `aria/cli/app.py`
- Modify: `pyproject.toml` (add `typer` dependency, add `aria` console script)
- Test: `tests/test_cli_app.py`

**Interfaces:**
- Consumes: `aria.__version__` (already exists in `aria/__init__.py`).
- Produces: `app = typer.Typer(...)` and `cli_main() -> None` in `aria.cli.app`. Tasks 6-9 add `@app.command()` functions to this same module.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli_app.py`:

```python
"""Tests for the aria CLI scaffold (--version, base app)."""

from typer.testing import CliRunner

from aria import __version__
from aria.cli.app import app

runner = CliRunner()


def test_version_flag_prints_version_and_exits():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_app.py -v`
Expected: FAILED with `ModuleNotFoundError: No module named 'typer'` (not yet a dependency) and/or `No module named 'aria.cli'`

- [ ] **Step 3: Add the `typer` dependency and write the scaffold**

Modify `pyproject.toml` — add `"typer>=0.12"` to the `dependencies` list (after line 30, `"requests>=2.31",`):

```toml
dependencies = [
    "networkx>=3.0",
    "numpy>=1.24",
    "pandas>=2.0",
    "scikit-learn>=1.3",
    "sentence-transformers>=2.2",
    "requests>=2.31",
    "typer>=0.12",
]
```

Add `aria` to `[project.scripts]`:

```toml
[project.scripts]
aria-benchmark = "aria.evaluation.benchmark:main"
aria = "aria.cli.app:cli_main"
```

Install it: `pip install -e .`

Create `aria/cli/__init__.py`:

```python
"""ARIA command-line interface package."""
```

Create `aria/cli/app.py`:

```python
"""ARIA command-line interface.

Every command here does nothing but parse arguments, call
`aria.engine_factory` + `ARIAEngine`/`KGDiagnostics`, and format the
result. No reasoning logic lives in this module.
"""

from __future__ import annotations

import typer

from aria import __version__

app = typer.Typer(add_completion=False, help="ARIA: causal-aware reasoning for materials discovery.")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"aria-materials {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """ARIA command-line interface."""


def cli_main() -> None:
    app()


if __name__ == "__main__":
    cli_main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_app.py -v`
Expected: 2 PASSED

Also verify the console script works end to end: `aria --version` should print `aria-materials 0.1.0`.

- [ ] **Step 5: Commit**

```bash
git add aria/cli/__init__.py aria/cli/app.py pyproject.toml tests/test_cli_app.py
git commit -m "feat: scaffold aria CLI with typer, add console script"
```

---

### Task 5: `aria/cli/formatting.py` — human-readable rendering

**Files:**
- Create: `aria/cli/formatting.py`
- Test: `tests/test_cli_formatting.py`

**Interfaces:**
- Consumes: `aria.types.ARIAResult`, `aria.kg.diagnostics.KGDiagnostics.print_report`.
- Produces: `format_result_summary(result: ARIAResult) -> str`, `format_explain(result: ARIAResult) -> str`, `format_diagnostics_report(report: dict) -> str`. Tasks 6-9 import these.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_formatting.py`:

```python
"""Tests for aria.cli.formatting."""

from aria.types import ARIAResult, ChainOfThought, ReasoningStep, ReasoningTier
from aria.cli.formatting import format_diagnostics_report, format_explain, format_result_summary


def _make_result(**overrides) -> ARIAResult:
    defaults = dict(
        answer={"carrier_mobility": "high"},
        tier=ReasoningTier.DIRECT,
        confidence=0.85,
        reasoning_type="direct_path",
        causal_trace=[],
        missing_evidence=[],
        kg_paths_used=2,
        kg_paths=["A -> B -> C"],
        literature_papers=[],
        source_attribution={},
        chain_of_thought=None,
        mode="aria",
        model="qwen2:7b",
        latency_ms=123.4,
    )
    defaults.update(overrides)
    return ARIAResult(**defaults)


def test_format_result_summary_includes_key_fields():
    result = _make_result()
    text = format_result_summary(result)
    assert "DIRECT" in text
    assert "0.85" in text
    assert "carrier_mobility" in text


def test_format_result_summary_lists_missing_evidence():
    result = _make_result(missing_evidence=["no crystallinity data"])
    text = format_result_summary(result)
    assert "no crystallinity data" in text


def test_format_explain_without_chain_of_thought():
    result = _make_result(chain_of_thought=None)
    text = format_explain(result)
    assert "No chain-of-thought available" in text


def test_format_explain_with_chain_of_thought():
    cot = ChainOfThought(
        reasoning_steps=[
            ReasoningStep(
                step_id="kg_retrieval",
                description="Found 2 paths",
                confidence=1.0,
                intermediate_conclusion="Tier 1 selected",
            )
        ],
    )
    result = _make_result(chain_of_thought=cot)
    text = format_explain(result)
    assert "kg_retrieval" in text
    assert "Tier 1 selected" in text


def test_format_diagnostics_report_renders_structure_section():
    report = {
        "kg_file": "demo.json",
        "structure": {
            "num_nodes": 10, "num_edges": 5, "density": 0.1, "avg_degree": 1.0,
            "num_root_nodes": 2, "num_leaf_nodes": 3, "num_intermediate_nodes": 5,
            "is_dag": True, "longest_path_length": 3, "weakly_connected_components": 1,
        },
        "content": {
            "mechanism_coverage": 0.5, "edges_with_mechanism": 2, "edges_without_mechanism": 3,
            "avg_mechanism_length": 20.0, "property_coverage": 0.4, "avg_confidence": 0.9,
            "num_unique_properties": 3,
        },
        "coverage": {
            "total_queries": 5, "queries_with_match": 3, "queries_without_match": 2,
            "avg_paths_per_query": 1.2, "coverage_rate": 0.6,
        },
        "diversity": {"diversity_score": 0.7, "avg_similarity": 0.3},
        "gaps": {
            "current_coverage": 0.6,
            "coverage_estimates": {"50%_coverage": {"additional_edges_needed": 0}},
            "papers_needed_estimates": {},
            "recommendation": "GOOD: Good size and coverage.",
        },
    }
    text = format_diagnostics_report(report)
    assert "KNOWLEDGE GRAPH QUALITY DIAGNOSTIC REPORT" in text
    assert "GOOD: Good size and coverage." in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_formatting.py -v`
Expected: FAILED with `ModuleNotFoundError: No module named 'aria.cli.formatting'`

- [ ] **Step 3: Write the implementation**

Create `aria/cli/formatting.py`:

```python
"""Human-readable rendering of ARIA results and KG diagnostics reports."""

from __future__ import annotations

import contextlib
import io
from typing import Any, Dict

from aria.types import ARIAResult


def format_result_summary(result: ARIAResult) -> str:
    """Render a short human-readable summary of an ARIAResult."""
    lines = [
        f"Tier:        {result.tier.name} ({result.tier.value})",
        f"Confidence:  {result.confidence:.2f}",
        f"Mode:        {result.mode}",
        f"Reasoning:   {result.reasoning_type}",
        f"KG paths:    {result.kg_paths_used}",
        f"Latency:     {result.latency_ms:.0f} ms",
        "",
        "Answer:",
    ]
    for key, value in result.answer.items():
        lines.append(f"  {key}: {value}")
    if result.missing_evidence:
        lines.append("")
        lines.append("Missing evidence:")
        for item in result.missing_evidence:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def format_explain(result: ARIAResult) -> str:
    """Render the full chain-of-thought + causal trace for `aria explain`."""
    lines = [format_result_summary(result), ""]
    if result.chain_of_thought is not None:
        lines.append("Chain of thought:")
        for step in result.chain_of_thought.reasoning_steps:
            lines.append(f"  [{step.step_id}] {step.description} (confidence={step.confidence:.2f})")
            if step.intermediate_conclusion:
                lines.append(f"      -> {step.intermediate_conclusion}")
    else:
        lines.append("No chain-of-thought available (mode did not produce one).")
    if result.causal_trace:
        lines.append("")
        lines.append("Causal trace:")
        for step in result.causal_trace:
            lines.append(f"  - {step.evidence_text} (confidence={step.confidence:.2f})")
    if result.literature_papers:
        lines.append("")
        lines.append(f"Literature ({len(result.literature_papers)} papers):")
        for paper in result.literature_papers[:10]:
            lines.append(f"  - {paper.get('title', 'Untitled')} ({paper.get('year', 'n/a')})")
    return "\n".join(lines)


def format_diagnostics_report(report: Dict[str, Any]) -> str:
    """Render a `KGDiagnostics.generate_report()` dict as human-readable text."""
    from aria.kg.diagnostics import KGDiagnostics

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        KGDiagnostics.print_report(report)
    return buf.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_formatting.py -v`
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add aria/cli/formatting.py tests/test_cli_formatting.py
git commit -m "feat: add CLI result/diagnostics formatting"
```

---

### Task 6: `aria predict` command

**Files:**
- Modify: `aria/cli/app.py`
- Test: `tests/test_cli_predict.py`

**Interfaces:**
- Consumes: `aria.engine_factory.{resolve_kg_path, build_engine, parse_kv_pairs, OllamaUnavailableError}`, `aria.cli.formatting.format_result_summary`.
- Produces: `predict` Typer command and the shared `_build_processing()` helper (also used by Task 8's `explain`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_predict.py`:

```python
"""Tests for `aria predict`."""

import pytest
from typer.testing import CliRunner

from aria.cli.app import app

runner = CliRunner()


def test_predict_rejects_unknown_mode():
    result = runner.invoke(
        app,
        [
            "predict", "--material", "MoS2", "--target-property", "carrier mobility",
            "--mode", "not_a_real_mode",
        ],
    )
    assert result.exit_code == 1
    assert "Unknown mode" in result.stdout


def test_predict_rejects_missing_kg_file():
    result = runner.invoke(
        app,
        [
            "predict", "--material", "MoS2", "--target-property", "carrier mobility",
            "--kg", "/nonexistent/kg.json",
        ],
    )
    assert result.exit_code == 1
    assert "KG file not found" in result.stdout


@pytest.mark.slow
def test_predict_happy_path_json_output():
    """Requires a live Ollama server with qwen2:7b pulled."""
    result = runner.invoke(
        app,
        [
            "predict", "--material", "MoS2", "--target-property", "carrier mobility",
            "--temperature", "750C", "--method", "CVD", "--json",
        ],
    )
    assert result.exit_code == 0
    assert '"tier"' in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_predict.py -v -k "not slow"`
Expected: FAILED — `predict` is not a registered command yet (Typer reports "No such command")

- [ ] **Step 3: Implement the `predict` command**

Modify `aria/cli/app.py` — add these imports at the top (alongside the existing `typer` import):

```python
import json
from typing import List, Optional

from aria.cli.formatting import format_result_summary
from aria.engine_factory import OllamaUnavailableError, build_engine, parse_kv_pairs, resolve_kg_path
```

Append to `aria/cli/app.py`:

```python
def _build_processing(
    temperature: Optional[str],
    method: Optional[str],
    atmosphere: Optional[str],
    substrate: Optional[str],
    param: List[str],
) -> dict:
    processing = parse_kv_pairs(param)
    if temperature is not None:
        processing["temperature"] = temperature
    if method is not None:
        processing["method"] = method
    if atmosphere is not None:
        processing["atmosphere"] = atmosphere
    if substrate is not None:
        processing["substrate"] = substrate
    return processing


@app.command()
def predict(
    material: str = typer.Option(..., help="Host material, e.g. MoS2"),
    target_property: str = typer.Option(..., "--target-property", help="Property to predict, e.g. 'carrier mobility'"),
    temperature: Optional[str] = typer.Option(None, help="Processing temperature, e.g. 750C"),
    method: Optional[str] = typer.Option(None, help="Synthesis method, e.g. CVD"),
    atmosphere: Optional[str] = typer.Option(None, help="Synthesis atmosphere, e.g. Ar"),
    substrate: Optional[str] = typer.Option(None, help="Substrate material"),
    param: List[str] = typer.Option([], "--param", help="Additional processing key=value pair (repeatable)"),
    mode: str = typer.Option("aria", help="Engine mode: baseline, naive_kg, aria, aria_search, aria_full"),
    kg: Optional[str] = typer.Option(None, "--kg", help="Path to a KG JSON file (defaults to the bundled demo KG)"),
    model: str = typer.Option("qwen2:7b", help="LLM model name"),
    json_output: bool = typer.Option(False, "--json", help="Print full ARIAResult as JSON"),
) -> None:
    """Predict material properties from synthesis conditions."""
    try:
        processing = _build_processing(temperature, method, atmosphere, substrate, param)
        kg_path = resolve_kg_path(kg)
        engine = build_engine(kg_path, model=model, mode=mode)
    except (FileNotFoundError, ValueError, OllamaUnavailableError) as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    result = engine.forward_predict(material=material, processing=processing, target_property=target_property)
    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        typer.echo(format_result_summary(result))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_predict.py -v -k "not slow"`
Expected: 2 PASSED (run the `slow` test separately with Ollama running to confirm the happy path)

- [ ] **Step 5: Commit**

```bash
git add aria/cli/app.py tests/test_cli_predict.py
git commit -m "feat: add aria predict command"
```

---

### Task 7: `aria design` command

**Files:**
- Modify: `aria/cli/app.py`
- Test: `tests/test_cli_design.py`

**Interfaces:**
- Consumes: same as Task 6, plus `_build_processing` reused for the `--constraint`/`--method` inputs.
- Produces: `design` Typer command.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_design.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_design.py -v -k "not slow"`
Expected: FAILED — `design` is not a registered command yet

- [ ] **Step 3: Implement the `design` command**

Append to `aria/cli/app.py`:

```python
@app.command()
def design(
    target_material: str = typer.Option(..., "--target-material"),
    target_property: str = typer.Option(..., "--target-property"),
    method: Optional[str] = typer.Option(None, help="Constraint: synthesis method, e.g. CVD"),
    constraint: List[str] = typer.Option([], "--constraint", help="Additional constraint key=value pair (repeatable)"),
    mode: str = typer.Option("aria"),
    kg: Optional[str] = typer.Option(None, "--kg"),
    model: str = typer.Option("qwen2:7b"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Design synthesis conditions to achieve a desired property."""
    try:
        constraints = parse_kv_pairs(constraint)
        if method is not None:
            constraints["method"] = method
        kg_path = resolve_kg_path(kg)
        engine = build_engine(kg_path, model=model, mode=mode)
    except (FileNotFoundError, ValueError, OllamaUnavailableError) as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    result = engine.inverse_design(
        target_material=target_material, target_property=target_property, constraints=constraints
    )
    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        typer.echo(format_result_summary(result))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_design.py -v -k "not slow"`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add aria/cli/app.py tests/test_cli_design.py
git commit -m "feat: add aria design command"
```

---

### Task 8: `aria explain` command

**Files:**
- Modify: `aria/cli/app.py`
- Test: `tests/test_cli_explain.py`

**Interfaces:**
- Consumes: `_build_processing` (Task 6), `format_explain` (Task 5), `build_engine`/`resolve_kg_path` (Task 3/2).
- Produces: `explain` Typer command.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_explain.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_explain.py -v -k "not slow"`
Expected: FAILED — `explain` is not a registered command yet

- [ ] **Step 3: Implement the `explain` command**

Modify `aria/cli/app.py` — add `format_explain` to the existing `from aria.cli.formatting import ...` line so it reads:

```python
from aria.cli.formatting import format_explain, format_result_summary
```

Append to `aria/cli/app.py`:

```python
@app.command()
def explain(
    direction: str = typer.Option(..., help="'forward' or 'inverse'"),
    material: Optional[str] = typer.Option(None, help="Required for --direction forward"),
    target_material: Optional[str] = typer.Option(None, "--target-material", help="Required for --direction inverse"),
    target_property: str = typer.Option(..., "--target-property"),
    temperature: Optional[str] = typer.Option(None),
    method: Optional[str] = typer.Option(None),
    atmosphere: Optional[str] = typer.Option(None),
    substrate: Optional[str] = typer.Option(None),
    param: List[str] = typer.Option([], "--param"),
    kg: Optional[str] = typer.Option(None, "--kg"),
    model: str = typer.Option("qwen2:7b"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Run a query in aria_full mode and print the full reasoning trace."""
    if direction not in ("forward", "inverse"):
        typer.echo("`--direction` must be 'forward' or 'inverse'")
        raise typer.Exit(code=1)

    try:
        kg_path = resolve_kg_path(kg)
        engine = build_engine(kg_path, model=model, mode="aria_full")
    except (FileNotFoundError, ValueError, OllamaUnavailableError) as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    if direction == "forward":
        if not material:
            typer.echo("`--material` is required for --direction forward")
            raise typer.Exit(code=1)
        processing = _build_processing(temperature, method, atmosphere, substrate, param)
        result = engine.forward_predict(material=material, processing=processing, target_property=target_property)
    else:
        if not target_material:
            typer.echo("`--target-material` is required for --direction inverse")
            raise typer.Exit(code=1)
        constraints = _build_processing(temperature, method, atmosphere, substrate, param)
        result = engine.inverse_design(
            target_material=target_material, target_property=target_property, constraints=constraints
        )

    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        typer.echo(format_explain(result))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_explain.py -v -k "not slow"`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add aria/cli/app.py tests/test_cli_explain.py
git commit -m "feat: add aria explain command"
```

---

### Task 9: `aria diagnose` command

**Files:**
- Modify: `aria/cli/app.py`
- Test: `tests/test_cli_diagnose.py`

**Interfaces:**
- Consumes: `aria.kg.diagnostics.KGDiagnostics`, `format_diagnostics_report` (Task 5), `resolve_kg_path` (Task 2).
- Produces: `diagnose` Typer command.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_diagnose.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_diagnose.py -v -k "not slow"`
Expected: FAILED — `diagnose` is not a registered command yet

- [ ] **Step 3: Implement the `diagnose` command**

Append to `aria/cli/app.py`:

```python
@app.command()
def diagnose(
    kg: Optional[str] = typer.Option(None, "--kg"),
    save_json: Optional[str] = typer.Option(None, "--save-json"),
) -> None:
    """Run knowledge-graph quality diagnostics."""
    from aria.kg.diagnostics import KGDiagnostics

    try:
        kg_path = resolve_kg_path(kg)
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    diag = KGDiagnostics(kg_path)
    report = diag.generate_report()
    if save_json:
        KGDiagnostics.save_report(report, save_json)
    typer.echo(format_diagnostics_report(report))
```

Modify the `from aria.cli.formatting import ...` line so it reads:

```python
from aria.cli.formatting import format_diagnostics_report, format_explain, format_result_summary
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_diagnose.py -v -k "not slow"`
Expected: 1 PASSED (the two `slow` tests need `sentence-transformers` to actually download/run a model — run them separately)

- [ ] **Step 5: Commit**

```bash
git add aria/cli/app.py tests/test_cli_diagnose.py
git commit -m "feat: add aria diagnose command"
```

---

### Task 10: Full CLI smoke test — run all 4 commands against the bundled tiny KG

**Files:**
- Test: `tests/test_cli_smoke.py`

**Interfaces:**
- Consumes: everything from Tasks 4-9. This task adds no new production code — it's an integration checkpoint before starting the MCP work.

- [ ] **Step 1: Write the test**

Create `tests/test_cli_smoke.py`:

```python
"""End-to-end smoke test: `aria --help` and each subcommand's --help work."""

from typer.testing import CliRunner

from aria.cli.app import app

runner = CliRunner()


def test_help_lists_all_four_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("predict", "design", "explain", "diagnose"):
        assert command in result.stdout


def test_each_subcommand_help_runs_without_error():
    for command in ("predict", "design", "explain", "diagnose"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0, f"`aria {command} --help` failed: {result.stdout}"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_smoke.py -v`
Expected: 2 PASSED (this should already pass given Tasks 4-9 are complete — it's a regression guard, not new behavior; if it fails, fix the command registration in `aria/cli/app.py` before continuing)

- [ ] **Step 3: Run the full fast test suite to confirm nothing regressed**

Run: `python -m pytest tests/ -v -k "not slow"`
Expected: All PASSED

- [ ] **Step 4: Commit**

```bash
git add tests/test_cli_smoke.py
git commit -m "test: add CLI smoke test covering all four subcommands"
```

---

### Task 11: MCP scaffold — `aria/mcp/server.py` base, `aria-mcp` console script, Python 3.10 bump

**Files:**
- Create: `aria/mcp/__init__.py`
- Create: `aria/mcp/server.py`
- Create: `aria/mcp/__main__.py`
- Modify: `pyproject.toml` (add `mcp` dependency, bump `requires-python` and ruff `target-version`, add `aria-mcp` console script)
- Test: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: `aria.engine_factory.{resolve_kg_path, build_engine, OllamaUnavailableError}`.
- Produces: `mcp = FastMCP("aria")` instance and `main() -> None` in `aria.mcp.server`. Tasks 12-15 register `@mcp.tool()` functions in this module.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp_server.py`:

```python
"""Tests for the aria-mcp server."""

from aria.mcp.server import mcp


def test_mcp_server_is_named_aria():
    assert mcp.name == "aria"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mcp_server.py -v`
Expected: FAILED with `ModuleNotFoundError: No module named 'mcp'` (not yet a dependency) and/or `No module named 'aria.mcp'`

- [ ] **Step 3: Bump Python floor, add the `mcp` dependency, write the scaffold**

The official `mcp` PyPI package requires Python >=3.10 (confirmed against `pypi.org/pypi/mcp/json`). Modify `pyproject.toml`:

Change line 11 from:
```toml
requires-python = ">=3.9"
```
to:
```toml
requires-python = ">=3.10"
```

Add `"mcp>=1.2"` to the `dependencies` list (after the `"typer>=0.12",` line added in Task 4):

```toml
dependencies = [
    "networkx>=3.0",
    "numpy>=1.24",
    "pandas>=2.0",
    "scikit-learn>=1.3",
    "sentence-transformers>=2.2",
    "requests>=2.31",
    "typer>=0.12",
    "mcp>=1.2",
]
```

Add `aria-mcp` to `[project.scripts]`:

```toml
[project.scripts]
aria-benchmark = "aria.evaluation.benchmark:main"
aria = "aria.cli.app:cli_main"
aria-mcp = "aria.mcp.server:main"
```

Change the ruff target version from:
```toml
target-version = "py39"
```
to:
```toml
target-version = "py310"
```

Install it: `pip install -e .`

Create `aria/mcp/__init__.py`:

```python
"""ARIA MCP server package."""
```

Create `aria/mcp/server.py`:

```python
"""ARIA MCP server — exposes predict/design/explain/diagnose as MCP tools.

Every tool here does nothing but validate input, call
`aria.engine_factory` + `ARIAEngine`/`KGDiagnostics`, and return
`.to_dict()`. No reasoning logic lives in this module.
"""

from __future__ import annotations

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from aria.engine_factory import OllamaUnavailableError

mcp = FastMCP("aria")


def _error(exc: Exception) -> Dict[str, Any]:
    hint = ""
    if isinstance(exc, OllamaUnavailableError):
        hint = "Start Ollama with `ollama serve` and pull the model, e.g. `ollama pull qwen2:7b`."
    return {"error": str(exc), "hint": hint}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

Create `aria/mcp/__main__.py`:

```python
"""Allows `python -m aria.mcp` as an alternative to the `aria-mcp` console script."""

from aria.mcp.server import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mcp_server.py -v`
Expected: 1 PASSED

Also verify the console script is wired up: `aria-mcp --help` should not raise an import error (it will block waiting for stdio input if run without `--help`; Ctrl+C to exit if you run it manually).

- [ ] **Step 5: Commit**

```bash
git add aria/mcp/__init__.py aria/mcp/server.py aria/mcp/__main__.py pyproject.toml tests/test_mcp_server.py
git commit -m "feat: scaffold aria-mcp server, bump requires-python to 3.10 for mcp SDK"
```

---

### Task 12: MCP tool `predict`

**Files:**
- Modify: `aria/mcp/server.py`
- Modify: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: `_error()` (Task 11), `resolve_kg_path`/`build_engine` (Task 2/3).
- Produces: `predict(...)` MCP tool function, callable directly in tests as a plain Python function (FastMCP's `@mcp.tool()` decorator registers but does not wrap the function).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mcp_server.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mcp_server.py -v -k "not slow"`
Expected: FAILED with `ImportError: cannot import name 'predict'`

- [ ] **Step 3: Implement the `predict` tool**

Append to `aria/mcp/server.py` (before `def main():`):

```python
from typing import Optional

from aria.engine_factory import build_engine, resolve_kg_path


@mcp.tool()
def predict(
    material: str,
    target_property: str,
    processing: Optional[Dict[str, str]] = None,
    mode: str = "aria",
    kg: Optional[str] = None,
    model: str = "qwen2:7b",
) -> Dict[str, Any]:
    """Predict material properties from synthesis conditions."""
    try:
        kg_path = resolve_kg_path(kg)
        engine = build_engine(kg_path, model=model, mode=mode)
    except (FileNotFoundError, ValueError, OllamaUnavailableError) as exc:
        return _error(exc)

    result = engine.forward_predict(
        material=material, processing=processing or {}, target_property=target_property
    )
    return result.to_dict()
```

Move the `from typing import Optional` and `from aria.engine_factory import build_engine, resolve_kg_path` lines to the top of the file, alongside the existing imports, so the final import block reads:

```python
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from aria.engine_factory import OllamaUnavailableError, build_engine, resolve_kg_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mcp_server.py -v -k "not slow"`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add aria/mcp/server.py tests/test_mcp_server.py
git commit -m "feat: add aria-mcp predict tool"
```

---

### Task 13: MCP tool `design`

**Files:**
- Modify: `aria/mcp/server.py`
- Modify: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: same as Task 12.
- Produces: `design(...)` MCP tool function.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mcp_server.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mcp_server.py -v -k "not slow"`
Expected: FAILED with `ImportError: cannot import name 'design'`

- [ ] **Step 3: Implement the `design` tool**

Append to `aria/mcp/server.py` (before `def main():`):

```python
@mcp.tool()
def design(
    target_material: str,
    target_property: str,
    constraints: Optional[Dict[str, str]] = None,
    mode: str = "aria",
    kg: Optional[str] = None,
    model: str = "qwen2:7b",
) -> Dict[str, Any]:
    """Design synthesis conditions to achieve a desired property."""
    try:
        kg_path = resolve_kg_path(kg)
        engine = build_engine(kg_path, model=model, mode=mode)
    except (FileNotFoundError, ValueError, OllamaUnavailableError) as exc:
        return _error(exc)

    result = engine.inverse_design(
        target_material=target_material, target_property=target_property, constraints=constraints or {}
    )
    return result.to_dict()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mcp_server.py -v -k "not slow"`
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add aria/mcp/server.py tests/test_mcp_server.py
git commit -m "feat: add aria-mcp design tool"
```

---

### Task 14: MCP tool `explain`

**Files:**
- Modify: `aria/mcp/server.py`
- Modify: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: same as Task 12.
- Produces: `explain(...)` MCP tool function.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mcp_server.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mcp_server.py -v -k "not slow"`
Expected: FAILED with `ImportError: cannot import name 'explain'`

- [ ] **Step 3: Implement the `explain` tool**

Append to `aria/mcp/server.py` (before `def main():`):

```python
@mcp.tool()
def explain(
    direction: str,
    target_property: str,
    material: Optional[str] = None,
    target_material: Optional[str] = None,
    processing: Optional[Dict[str, str]] = None,
    kg: Optional[str] = None,
    model: str = "qwen2:7b",
) -> Dict[str, Any]:
    """Run a query in aria_full mode and return the full reasoning trace."""
    if direction not in ("forward", "inverse"):
        return {"error": "`direction` must be 'forward' or 'inverse'", "hint": ""}

    try:
        kg_path = resolve_kg_path(kg)
        engine = build_engine(kg_path, model=model, mode="aria_full")
    except (FileNotFoundError, ValueError, OllamaUnavailableError) as exc:
        return _error(exc)

    if direction == "forward":
        if not material:
            return {"error": "`material` is required when direction='forward'", "hint": ""}
        result = engine.forward_predict(
            material=material, processing=processing or {}, target_property=target_property
        )
    else:
        if not target_material:
            return {"error": "`target_material` is required when direction='inverse'", "hint": ""}
        result = engine.inverse_design(
            target_material=target_material,
            target_property=target_property,
            constraints=processing or {},
        )
    return result.to_dict()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mcp_server.py -v -k "not slow"`
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add aria/mcp/server.py tests/test_mcp_server.py
git commit -m "feat: add aria-mcp explain tool"
```

---

### Task 15: MCP tool `diagnose`

**Files:**
- Modify: `aria/mcp/server.py`
- Modify: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: `aria.kg.diagnostics.KGDiagnostics`, `resolve_kg_path` (Task 2).
- Produces: `diagnose(...)` MCP tool function.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mcp_server.py`:

```python
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
```

Add `import pytest` at the top of `tests/test_mcp_server.py` if it isn't already there.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mcp_server.py -v -k "not slow"`
Expected: FAILED with `ImportError: cannot import name 'diagnose'`

- [ ] **Step 3: Implement the `diagnose` tool**

Append to `aria/mcp/server.py` (before `def main():`):

```python
@mcp.tool()
def diagnose(kg: Optional[str] = None) -> Dict[str, Any]:
    """Run knowledge-graph quality diagnostics."""
    from aria.kg.diagnostics import KGDiagnostics

    try:
        kg_path = resolve_kg_path(kg)
    except FileNotFoundError as exc:
        return _error(exc)

    diag = KGDiagnostics(kg_path)
    return diag.generate_report()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mcp_server.py -v -k "not slow"`
Expected: 9 PASSED

- [ ] **Step 5: Commit**

```bash
git add aria/mcp/server.py tests/test_mcp_server.py
git commit -m "feat: add aria-mcp diagnose tool"
```

---

### Task 16: README — CLI quickstart, `.mcp.json` snippet, known-limitations note

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing new. This is documentation only.

- [ ] **Step 1: Identify the manual verification command**

No automated test applies to documentation content. Instead, this task is verified manually in Step 3:

Run: `aria predict --material MoS2 --target-property "carrier mobility" --temperature 750C --method CVD` (requires Ollama running) and confirm the output matches what the new README quickstart section will describe.

- [ ] **Step 2: Update README.md**

Find this block in `README.md` (in the "## Installation" section):

```markdown
## Installation

```bash
pip install aria-materials
```

For development with all optional dependencies:
```bash
pip install -e ".[all]"
```
```

Replace it with:

```markdown
## Installation

`aria-materials` is not yet published to PyPI — install from source:

```bash
git clone https://github.com/yicao-elina/ARIA.git
cd ARIA
pip install -e .
```

For development with all optional dependencies:
```bash
pip install -e ".[all]"
```

**Known limitation:** ARIA currently requires a local [Ollama](https://ollama.com) server (`ollama serve`, with a model pulled via `ollama pull qwen2:7b`). OpenAI-backend support is not yet implemented.

## CLI quickstart

Once installed, the bundled demo knowledge graph lets you run a query with zero configuration:

```bash
aria predict --material MoS2 --target-property "carrier mobility" \
  --temperature 750C --method CVD
```

Other commands: `aria design` (inverse design), `aria explain` (full reasoning trace), `aria diagnose` (KG quality report). Run `aria --help` or `aria <command> --help` for all options. Add `--json` to any of `predict`/`design`/`explain` for machine-readable output.

## MCP server

`aria-mcp` exposes the same four operations (`predict`, `design`, `explain`, `diagnose`) as MCP tools over stdio, for use from Claude Desktop, Claude Code, or any other MCP host:

```json
{
  "mcpServers": {
    "aria": {
      "command": "aria-mcp"
    }
  }
}
```

Or register it directly with Claude Code:

```bash
claude mcp add --transport stdio aria -- aria-mcp
```
```

- [ ] **Step 3: Verify**

Run the command from Step 1 (`aria predict ...`) and confirm its output matches what the new quickstart section describes. Also run `aria --help` and `aria-mcp --help`, and re-read the diff to confirm no other installation instructions in the file still reference `pip install aria-materials` without the "not yet published" caveat.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add CLI quickstart, MCP server setup, Ollama limitation note"
```
