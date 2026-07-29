# ARIA CLI + MCP Server — Design

**Date:** 2026-07-26
**Status:** Approved, implementation in progress
**Source:** Product-strategy artifact "Turning ARIA into an agent-native tool" (MCP vs. CLI, productization roadmap §6/§8)

## Problem

`ARIAEngine` (`aria/engine.py`) is a clean, unified entry point — five modes, one `ARIAResult` dataclass — but it is only reachable from Python. There is no query-facing CLI and no MCP server, so no agent runtime (Claude Code, Claude Desktop, LangGraph, a third-party auto-lab agent) can call ARIA without hand-writing a Python integration. This design adds both surfaces as thin wrappers over the existing engine, plus fixes two packaging bugs discovered while investigating current state.

## Confirmed current-state findings

- `ARIAEngine.forward_predict` / `.inverse_design` both return `ARIAResult` with `.to_dict()` / `.to_json()` — good shared contract for CLI and MCP to reuse as-is.
- No CLI beyond two dev entry points (`aria-benchmark`, `aria-diagnose`) declared in `pyproject.toml`.
- **`aria-diagnose = "aria.kg.diagnostics:main"` is broken** — `aria/kg/diagnostics.py` defines the `KGDiagnostics` class but no module-level `main()`. Running `aria-diagnose` today raises `AttributeError`.
- **`pyproject.toml`'s `package-data = {"aria" = ["data/*.json"]}` doesn't match reality.** The KG files (`aria_2d_kg_demo.json`, `aria_2d_kg_tiny.json`, the full `aria_2d_kg_v1.json`) live in the repo-root `data/` directory, not `aria/data/` (which is an empty stub package — just `__init__.py`). A `pip install aria-materials` today ships zero usable KG data.
- The engine hard-requires a local Ollama process. `ARIAEngine._create_llm_client()` only accepts `backend="ollama"` and raises `ValueError` otherwise. A `get_client()` factory in `aria/llm/client.py` *attempts* to support `backend="openai"` via a lazy import of `aria.llm.openai_client.OpenAIClient`, but that module does not exist, and `ARIAEngine` doesn't even call this factory. The OpenAI path is dead code, not a working alternative.
- `aria-materials` is not published to PyPI (confirmed 404).
- `.claude/skills/aria-run.md` documents the intended usage pattern (`forward_predict`/`inverse_design` args, `ARIAResult` fields, mode selection guide) — used below as the source of truth for CLI/MCP argument shapes.

## Decisions (confirmed with user)

1. **Scope:** CLI + MCP code only. No PyPI publish, no naming/positioning work in this pass.
2. **Package layout:** Subpackages inside the existing `aria-materials` package (`aria/cli/`, `aria/mcp/`), not a separate repo.
3. **LLM backend:** Ship requiring Ollama. Document it as a known limitation; do not implement the OpenAI backend in this pass.

## Architecture

```
aria/
├── engine.py                    # existing, untouched
├── data/
│   ├── __init__.py               # existing
│   ├── aria_2d_kg_demo.json      # NEW: copied here from repo-root data/ (kept there too)
│   └── aria_2d_kg_tiny.json      # NEW: bundled so pip installs ship a usable KG
├── engine_factory.py             # NEW: shared engine-construction + validation helper
├── cli/
│   ├── __init__.py
│   ├── app.py                    # NEW: Typer app — predict / design / explain / diagnose
│   └── formatting.py             # NEW: human-readable rendering of ARIAResult / KG reports
└── mcp/
    ├── __init__.py
    ├── server.py                  # NEW: FastMCP server, 4 tools mirroring the CLI
    └── __main__.py                 # NEW: `python -m aria.mcp` entry point
```

`engine_factory.py` exists so the CLI and MCP server cannot drift on how they load a KG, construct an `ARIAEngine`, validate a mode string, or report "Ollama isn't running" — both surfaces call the same functions.

### `engine_factory.py` contract

- `resolve_kg_path(kg_arg: Optional[str]) -> str` — if `kg_arg` given, use it; else resolve the bundled demo KG via `importlib.resources` (`aria.data`).
- `parse_kv_pairs(pairs: list[str]) -> dict` — turns repeated `key=value` CLI/MCP args into a dict; raises a clear `ValueError` on malformed input (no silent partial parsing).
- `build_engine(kg_path, model, mode, llm_backend="ollama", llm_base_url=...) -> ARIAEngine` — validates `mode` against `EngineMode`, constructs the engine, and wraps Ollama connection failures in a message that names the fix (`ollama serve`, `ollama pull <model>`) rather than a bare exception/traceback.

### Two packaging fixes bundled into this work

1. Bundle `aria_2d_kg_demo.json` and `aria_2d_kg_tiny.json` inside `aria/data/`; fix `pyproject.toml`'s `package-data` entry so they actually ship on `pip install`. The full 777-node KG stays repo-root-only (too large to bundle) and is reached via explicit `--kg`.
2. Remove the broken `aria-diagnose` console-script entry point from `pyproject.toml`. It's superseded by `aria diagnose`. Keep `aria-benchmark` (it has a working `main()`).

## CLI (`aria`, Typer)

| Command | Wraps | Options |
|---|---|---|
| `aria predict` | `ARIAEngine.forward_predict` | `--material`, `--temperature`, `--method`, `--atmosphere`, `--substrate`, `--param key=value` (repeatable, for anything not covered by named flags), `--target-property`, `--mode` (default `aria`), `--kg`, `--model` (default `qwen2:7b`), `--json` |
| `aria design` | `ARIAEngine.inverse_design` | `--target-material`, `--target-property`, `--constraint key=value` (repeatable), `--mode`, `--kg`, `--model`, `--json` |
| `aria explain` | forces `mode=aria_full` on predict/design | `--direction forward\|inverse` + the same inputs as the corresponding command; prints full chain-of-thought, causal trace, and literature sources |
| `aria diagnose` | `KGDiagnostics.generate_report` / `.print_report` | `--kg`, `--save-json PATH` |

Default output: short human-readable summary (answer, tier, confidence, reasoning type). `--json` prints `ARIAResult.to_dict()` (or the diagnostics report dict) for scripting.

Console script: `aria = "aria.cli.app:main"`.

## MCP server (`aria-mcp`, official `mcp` SDK / FastMCP, stdio transport)

Four tools — `predict`, `design`, `explain`, `diagnose` — mirroring the CLI 1:1. Each tool handler: validate input → `engine_factory.build_engine(...)` → call the matching `ARIAEngine`/`KGDiagnostics` method → return `.to_dict()`. No reasoning logic lives in `aria/mcp/`.

- Console script: `aria-mcp = "aria.mcp.server:main"`.
- README gets a `.mcp.json` snippet (`command: "aria-mcp"` for local/editable installs — the artifact's `uvx aria-mcp` form is deferred until PyPI publish, out of scope here) and a `claude mcp add --transport stdio aria -- aria-mcp` one-liner.
- If Ollama is unreachable at tool-call time, the tool returns a structured error object (`{"error": "...", "hint": "run `ollama serve`"}`), not a raw traceback — an MCP host should be able to surface this to its own user.

## Testing

- `engine_factory`: unit tests for `resolve_kg_path`, `parse_kv_pairs` (including malformed input), and mode validation — no LLM needed.
- CLI: Typer's `CliRunner`, one test module per subcommand, using the bundled tiny KG. Tests that need live inference are marked `@pytest.mark.slow` (existing repo convention).
- MCP: call the tool functions directly in-process (no need to spin up a real stdio transport for tests).

## Out of scope (explicit)

- PyPI publish (`pip install aria-materials` stays install-from-source for now; README documents this).
- Implementing `aria/llm/openai_client.py` — ARIA requires local Ollama; this is documented as a known limitation, not fixed here.
- Naming/positioning/messaging/outreach content from later sections of the source artifact.

## Implementation sequencing

CLI before MCP: it settles the input/output contract cheaply before that contract is frozen into an MCP tool schema. `engine_factory.py` is the shared prerequisite for both.

Phases: (1) `engine_factory.py` + packaging fixes → (2) CLI → (3) MCP server → (4) tests + README updates. Phase 1 is a hard prerequisite; phases 2–4 have internal parallelism opportunities once phase 1 lands.
