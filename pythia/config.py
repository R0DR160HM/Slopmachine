"""Static configuration shared across the application."""

import os
import subprocess
import sys

# Also writes the per-group docs that feed the search index
# (write_project_documentation).
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

# Model that embeds sources/docs for the project_search tool.
EMBED_MODEL = "embeddinggemma"

# embeddinggemma's context window is only 2k tokens — texts are sliced to
# ~1k tokens (≈4 chars per token) with a small overlap so no idea is cut
# exactly at a boundary.
EMBED_SLICE_CHARS = 4000
EMBED_SLICE_OVERLAP = 400

# Best-matching slices returned by one project_search call.
SEARCH_TOP_K = 5

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

# CPU threads handed to Ollama. The stdlib only exposes *logical* cores
# (os.cpu_count double-counts hyperthreads), so _physical_core_count() asks the
# OS for the physical count and falls back to the logical one when that fails.


def _physical_core_count() -> int:
    """Best-effort number of physical CPU cores on this machine."""
    try:
        if sys.platform == "darwin":
            out = subprocess.run(
                ["sysctl", "-n", "hw.physicalcpu"],
                capture_output=True, text=True, timeout=2,
            )
            return int(out.stdout.strip())
        if sys.platform.startswith("linux"):
            cores = set()
            phys_id = core_id = None
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("physical id"):
                        phys_id = line.split(":", 1)[1].strip()
                    elif line.startswith("core id"):
                        core_id = line.split(":", 1)[1].strip()
                    elif not line.strip() and phys_id is not None:
                        cores.add((phys_id, core_id))
                        phys_id = core_id = None
            if cores:
                return len(cores)
        if os.name == "nt":
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor | "
                 "Measure-Object -Property NumberOfCores -Sum).Sum"],
                capture_output=True, text=True, timeout=5,
            )
            return int(out.stdout.strip())
    except Exception:
        pass
    return os.cpu_count() or 1


# Leave 2 physical cores free by default so the machine stays usable while the
# model runs; --background-task clamps the thread count to this instead.
BACKGROUND_TASK_THREADS = 2
NUM_THREAD = max(1, _physical_core_count() - 2)

# Options passed on every ollama.chat() call. repeat_penalty is Ollama's
# default value, pinned so a model whose Modelfile disables it still gets it;
# repeat_last_n widens the penalty's horizon from the 64-token default so
# multi-line repetition loops are discouraged at generation time, before the
# streaming loop guard has to cut them off.
OLLAMA_OPTIONS = {
    "num_thread": NUM_THREAD,
    "num_ctx": NUM_CTX,
    "repeat_penalty": 1.1,
    "repeat_last_n": 256,
}

# Code Mode and the doc writer sample nearly greedily: Ollama's default
# temperature (~0.8) is what makes the agent flip-flop on its own edits and
# the docs embellish beyond the source.
CODE_OLLAMA_OPTIONS = {**OLLAMA_OPTIONS, "temperature": 0.2}

# Char budget for the conversation we send each turn. Roughly NUM_CTX * 4 chars
# per token, minus headroom for the model's own reply. Older turns beyond this
# are dropped — but the system prompt is always kept (see llm.trim_messages).
HISTORY_CHAR_BUDGET = 100_000

# Guard against infinite tool-call loops within a single user turn.
MAX_TOOL_CALLS = 10

# Repetition guard on EVERY streamed response (chat, docs, deep research,
# code...): when the last N complete lines already appeared earlier in the
# same response — verbatim, or identical after erasing list numbers/bullets —
# the model is looping; generation is stopped and the repeated tail removed.
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
