"""Shared helpers for building an ARIAEngine from CLI/MCP-style arguments.

Both `aria.cli` and `aria.mcp` call these functions so the two surfaces
cannot drift on KG resolution, argument parsing, or error messages.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional
from urllib.error import URLError
from urllib.request import urlopen

from aria.types import EngineMode

if TYPE_CHECKING:
    from aria.engine import ARIAEngine


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


class OllamaUnavailableError(RuntimeError):
    """Raised when the configured Ollama backend cannot be reached."""


def build_engine(
    kg_path: str,
    model: str = "qwen2:7b",
    mode: str = "aria",
    llm_backend: str = "ollama",
    llm_base_url: str = "http://localhost:11434",
) -> "ARIAEngine":
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

    # Lazy import: aria.engine pulls in networkx/sentence-transformers at
    # module level, matching the lazy-import convention aria/__init__.py
    # already uses for the same reason. This keeps `import aria.engine_factory`
    # (and anything that imports it, like aria.cli/aria.mcp) cheap until a
    # caller actually needs to construct an engine.
    from aria.engine import ARIAEngine

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
