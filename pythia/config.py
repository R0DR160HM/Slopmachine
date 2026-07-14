"""Static configuration shared across the application."""

# Also writes the per-file docs (write_project_documentation).
DEFAULT_MODEL = "qwen2.5:1.5b"

# Model activated when the user mentions "megabrain" in a message.
MEGABRAIN_MODEL = "qwen2.5:7b"

# Megabrain for Code Mode: a bigger coder instead of the general model.
CODE_MEGABRAIN_MODEL = "qwen2.5-coder:14b"

# Model used by tool_forge to write new tools in Python.
FORGE_MODEL = "qwen2.5-coder:7b"

# Model forced by --slop: the tiniest tier, used for EVERYTHING in that mode
# (chat, tool forging and per-file docs alike).
SLOP_MODEL = "qwen2.5:0.5b"

# Source chars fed to the doc-writing model per file group (fits NUM_CTX
# with room for the generated docs).
DOC_GROUP_MAX_CHARS = 20_000

# Chars of one project file handed to the model by Code Mode's read_file
# (fits NUM_CTX with room for the conversation and the rewritten file).
CODE_FILE_MAX_CHARS = 40_000

# Seconds the Code Mode session must sit idle (no user input, no running
# shells) after approved writes before the documentation/search index is
# refreshed automatically.
CODE_REINDEX_IDLE_SECONDS = 300

# The automatic post-change build is synchronous (its result goes back to the
# model in the same feedback message); a build stuck longer than this is
# terminated so the session never hangs.
CODE_BUILD_TIMEOUT_SECONDS = 600

# Upper bound of PlantUML diagrams generated per documented file group.
DOC_DIAGRAMS_MAX = 6

# Model that embeds sources/docs/diagrams for the project_search tool.
EMBED_MODEL = "embeddinggemma"

# embeddinggemma's context window is only 2k tokens — texts are sliced to
# ~1k tokens (≈4 chars per token) with a small overlap so no idea is cut
# exactly at a boundary.
EMBED_SLICE_CHARS = 4000
EMBED_SLICE_OVERLAP = 400

# Best-matching slices returned by one project_search call.
SEARCH_TOP_K = 5

# Chars of the just-written markdown doc appended to the diagram-selection
# prompt (on top of the truncated source).
DOC_DIAGRAM_DOC_MAX_CHARS = 8_000

# Max search results requested per query (overridable with --results).
DEFAULT_MAX_RESULTS = 5

# Output of a forged tool is truncated to this many chars before being fed
# back to the model, so a runaway tool cannot flood the context window.
FORGED_RESULT_MAX_CHARS = 4000

# Context window (tokens) sent to Ollama. Set explicitly so behaviour is
# predictable instead of relying on Ollama's small default (~2048-4096).
# The qwen2.5 family supports up to 32k; 30k leaves headroom for the
# model's reply.
NUM_CTX = 30_000

# Options passed on every ollama.chat() call.
OLLAMA_OPTIONS = {"num_thread": 8, "num_ctx": NUM_CTX}

# Code Mode samples nearly greedily: Ollama's default temperature (~0.8) is
# what makes the agent flip-flop on its own edits.
CODE_OLLAMA_OPTIONS = {**OLLAMA_OPTIONS, "temperature": 0.2}

# Char budget for the conversation we send each turn. Roughly NUM_CTX * 4 chars
# per token, minus headroom for the model's own reply. Older turns beyond this
# are dropped — but the system prompt is always kept (see llm.trim_messages).
HISTORY_CHAR_BUDGET = 100_000

# Guard against infinite tool-call loops within a single user turn.
MAX_TOOL_CALLS = 10

# Repetition guard on EVERY streamed response (chat, docs, deep research,
# code...): when the last N complete lines already appeared earlier in the
# same response, the model is looping — generation is stopped and the
# repeated tail removed.
STREAM_LOOP_WINDOW_LINES = 10

# Delphic maxims shown under the title — one is drawn at random per session.
DELPHIC_MAXIMS = (
    "Γνῶθι σεαυτόν — Conhece-te a ti mesmo",
    "Μηδὲν ἄγαν — Nada em excesso",
    "Καιρὸν γνῶθι — Conhece o momento certo",
    "Σοφίαν ζήλου — Busca a sabedoria",
    "Γνοὺς πρᾶττε — Age sabendo",
    "Φρόνει θνητά — Pensa como um mortal",
    "Μελέτει τὸ πᾶν — Contempla o todo",
    "Ἐγγύα, πάρα δ' ἄτα — Promete, e a ruína está próxima",
)

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

# ── Deep research mode ────────────────────────────────────────────────────────

# How many subtopics to drill into.
DEEP_SUBTOPICS = 4

# Top links to fetch full text from per research pass.
DEEP_FETCH_TOP = 2
