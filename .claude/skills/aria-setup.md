# ARIA Environment Setup

Configure the ARIA runtime environment: install the package, set up the knowledge graph, verify the LLM backend, and initialize the engine.

## Activation

When the user asks to set up, install, configure, or initialize ARIA, or mentions "aria-setup", "install ARIA", "configure ARIA", "initialize engine", or "check environment".

## Steps

### 1. Install the package

```bash
pip install -e ".[all]"
```

This installs ARIA in editable mode with all optional dependencies (sentence-transformers, spacy, visualization, dev tools). For a minimal install:

```bash
pip install -e .           # core only (no viz, no spacy)
pip install -e ".[dev]"    # core + dev tools (pytest, ruff, mypy)
```

Verify installation:

```bash
python -c "import aria; print(aria.__version__)"
```

### 2. Configure environment variables

Create a `.env` file in the project root (see `.env.example` for reference):

```
ARIA_LLM_BACKEND=ollama
ARIA_OLLAMA_MODEL=qwen2:7b
ARIA_EMBEDDING_MODEL=all-MiniLM-L6-v2
ARIA_SEARCH_EMAIL=your_email@institution.edu
```

| Variable | Description | Default |
|----------|-------------|---------|
| `ARIA_LLM_BACKEND` | LLM backend: `ollama` or `openai` | `ollama` |
| `ARIA_OLLAMA_MODEL` | Ollama model for generation | `qwen2:7b` |
| `ARIA_EMBEDDING_MODEL` | Sentence-transformer model for embeddings | `all-MiniLM-L6-v2` |
| `ARIA_SEARCH_EMAIL` | Email for OpenAlex polite pool and Semantic Scholar API | `research@example.com` |

Load the `.env` file before running ARIA:

```python
from dotenv import load_dotenv
load_dotenv()
```

### 3. Verify LLM connectivity

Ensure Ollama is running and the model is available:

```bash
ollama list                    # check available models
ollama pull qwen2:7b           # pull if not present
ollama serve                   # start the server
```

Then test the connection programmatically:

```python
from aria.llm.client import OllamaClient
client = OllamaClient(model="qwen2:7b")
connected = client.test_connection()
if connected:
    print("Ollama connection successful")
else:
    print("Ollama connection failed -- ensure ollama serve is running")
```

### 4. Load the knowledge graph

```python
from aria import ARIAEngine, load_kg

# Use the demo KG for tutorials (27 edges, complete P-S-P chains)
kg = load_kg("data/aria_2d_kg_demo.json")

# Use the tiny KG for minimal tests (6 edges)
# kg = load_kg("data/aria_2d_kg_tiny.json")

# Use the full KG for real experiments (must be generated first)
# kg = load_kg("data/aria_2d_kg_v1.json")
```

### 5. Initialize the engine

```python
from aria import ARIAEngine, load_kg

kg = load_kg("data/aria_2d_kg_demo.json")
engine = ARIAEngine(kg=kg, model="qwen2:7b", mode="aria")
```

Available modes (see `aria.types.EngineMode`):

| Mode | Description |
|------|-------------|
| `"baseline"` | Pure LLM, no KG (ablation control) |
| `"naive_kg"` | Simple KG + LLM concatenation (ablation control) |
| `"aria"` | Three-tier causal cascade (default, recommended) |
| `"aria_search"` | Three-tier + OpenAlex/Semantic Scholar literature search |
| `"aria_full"` | Three-tier + literature + chain-of-thought transparency |

### 6. Quick smoke test

```python
result = engine.forward_predict(
    material="MoS2",
    processing={"temperature": "750C", "method": "CVD"},
    target_property="carrier mobility",
)
print(f"Answer: {result.answer}")
print(f"Tier: {result.tier}")
print(f"Confidence: {result.confidence}")
```

## Troubleshooting

- **Ollama not running**: Start with `ollama serve` or check the daemon.
- **Model not found**: Run `ollama pull qwen2:7b` to download.
- **sentence-transformers download**: First run downloads embedding models (~100 MB). Ensure internet access.
- **spacy model missing**: Run `python -m spacy download en_core_web_sm` or let ARIA auto-download on first use.
- **KG file not found**: The full KG (`aria_2d_kg_v1.json`) is gitignored due to size. Use `data/aria_2d_kg_demo.json` (27 edges, for tutorials) or `data/aria_2d_kg_tiny.json` (6 edges, for tests).