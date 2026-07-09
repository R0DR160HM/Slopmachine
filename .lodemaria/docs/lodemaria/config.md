## File: lodemaria/config.py
"""Static configuration shared across the application."""

DEFAULT_MODEL = "qwen2.5:1.5b"

# Model activated when the user mentions "megabrain" in a message.
MEGABRAIN_MODEL = "qwen2.5:7b"

# Model used by tool_forge to write new tools in Python.
FORGE_MODEL = "qwen2.5-coder:7b"

# Models forced by --slop: the tiniest tier, for fast low-resource runs.
SLOP_MODEL = "qwen2.5:0.5b"
SLOP_FORGE_MODEL = "qwen2.5-coder:0.5b"

# Model used by write_project_documentation to write the per-file docs.
DOC_MODEL = "qwen2.5-coder:1.5b"

# Model that synthesizes the general PROJECT.md from the per-file docs —
# a prose task, so the general model fits better than the coder one.
DOC_SYNTH_MODEL = "qwen2.5:3b"

# Source chars fed to the doc model per file group (fits NUM_CTX with room
# for the generated docs).
DOC_GROUP_MAX_CHARS = 20_000

# Combined per-file docs fed to the doc model for the general PROJECT.md.
DOC_PROJECT_MAX_CHARS = 90_000

# Max search results requested per query (overridable with --results).
DEFAULT_MAX_RESULTS = 5

# Output of a forged tool is truncated to this many chars before being fed
# back to the model, so a runaway tool cannot flood the context window.
FORGED_RESULT_MAX_CHARS = 4000

# Context window (tokens) sent to Ollama. Set explicitly so behaviour is
# predictable instead of relying on Ollama's small default (~2048-4096).
NUM_CTX = 30_000

# Options passed on every ollama.chat() call.
OLLAMA_OPTIONS = {"num_thread": 8, "num_ctx": NUM_CTX}

# Char budget for the conversation we send each turn. Roughly NUM_CTX * 4 chars
# per token, minus headroom for the model's own reply. Older turns beyond this
# are dropped — but the system prompt is always kept (see llm.trim_messages).
HISTORY_CHAR_BUDGET = 100_000

# Guard against infinite tool-call loops within a single user turn.
MAX_TOOL_CALLS = 10

# Labels cycled through on the live "thinking" timer.
THINKING_LABELS = (
    "Pensando",
    "Imaginando",
    "Coletando recursos",
    "Elaborando",
    "Refletindo",
    "Processando",
    "Organizando ideias",
    "Consultando o oráculo",
    "Filosofando",
    "Ruminando",
)

## Deep research mode
