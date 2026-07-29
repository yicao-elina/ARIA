"""ARIA MCP server — exposes predict/design/explain/diagnose as MCP tools.

Every tool here does nothing but validate input, call
`aria.engine_factory` + `ARIAEngine`/`KGDiagnostics`, and return
`.to_dict()`. No reasoning logic lives in this module.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from aria.engine_factory import OllamaUnavailableError, build_engine, resolve_kg_path

mcp = FastMCP("aria")


def _error(exc: Exception) -> Dict[str, Any]:
    hint = ""
    if isinstance(exc, OllamaUnavailableError):
        hint = "Start Ollama with `ollama serve` and pull the model, e.g. `ollama pull qwen2:7b`."
    return {"error": str(exc), "hint": hint}


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


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
