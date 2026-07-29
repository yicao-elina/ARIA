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
