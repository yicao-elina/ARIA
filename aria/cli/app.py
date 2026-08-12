"""ARIA command-line interface.

Every command here does nothing but parse arguments, call
`aria.engine_factory` + `ARIAEngine`/`KGDiagnostics`, and format the
result. No reasoning logic lives in this module.
"""

from __future__ import annotations

import json
from typing import List, Optional

import typer

from aria import __version__
from aria.cli.formatting import format_diagnostics_report, format_explain, format_result_summary
from aria.engine_factory import (
    OllamaUnavailableError,
    build_engine,
    parse_kv_pairs,
    resolve_kg_path,
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="ARIA: causal-aware reasoning for materials discovery.",
)


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


def cli_main() -> None:
    app()


if __name__ == "__main__":
    cli_main()
