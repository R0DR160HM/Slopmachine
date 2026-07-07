# Configuration Settings for LODEMARIA

This file contains the static configuration settings shared across various components of the LODEMARIA application. These settings control aspects like model selection, character limits, and other parameters essential for the application's operation.

## Constants

- **DEFAULT_MODEL**: The default model used by the application.
  - *Type*: `str`
  - *Value*: `"qwen2.5:0.5b"`

- **MEGABRAIN_MODEL**: The model activated when the user mentions "megabrain" in a message.
  - *Type*: `str`
  - *Value*: `"qwen2.5:7b"`

- **FORGE_MODEL**: The model used by the tool_forge to write new tools in Python.
  - *Type*: `str`
  - *Value*: `"qwen2.5-coder:7b"`

- **DOC_MODEL**: The model used by write_project_documentation to write per-file docs.
  - *Type*: `str`
  - *Value*: `"qwen2.5-coder:7b"`

- **DOC_SYNTH_MODEL**: The model that synthesizes the general PROJECT.md from per-file docs, using a prose task.
  - *Type*: `str`
  - *Value*: `"qwen2.5:7b"`

- **DOC_GROUP_MAX_CHARS**: Source characters fed to the doc model per file group, fitting NUM_CTX with room for generated docs.
  - *Type*: `int`
  - *Value*: `20_000`

- **DOC_PROJECT_MAX_CHARS**: Combined per-file docs fed to the doc model for the general PROJECT.md.
  - *Type*: `int`
  - *Value*: `90_000`

- **DEFAULT_MAX_RESULTS**: Maximum search results requested per query, overridable with --results.
  - *Type*: `int`
  - *Value*: `5`

- **FORGED_RESULT_MAX_CHARS**: Output of a forged tool is truncated to this many characters before being fed back to the model.
  - *Type*: `int`
  - *Value*: `4000`

- **NUM_CTX**: Context window (tokens) sent to Ollama. Set explicitly for predictable behavior.
  - *Type*: `int`
  - *Value*: `30_000`

- **OLLAMA_OPTIONS**: Options passed on every ollama.chat() call.
  - *Type*: `dict`
  - *Content*:
    ```python
    {
        "num_thread": 8,
        "num_ctx": NUM_CTX
    }
    ```

- **HISTORY_CHAR_BUDGET**: Character budget for the conversation sent each turn.
  - *Type*: `int`
  - *Value*: `100_000`

- **MAX_TOOL_CALLS**: Maximum number of tool calls within a single user turn to guard against infinite loops.
  - *Type*: `int`
  - *Value*: `10`

- **THINKING_LABELS**: Labels cycled through on the live "thinking" timer.
  - *Type*: `tuple[str]`
  - *Values*:
    ```python
    (
        "Pensando",
        "Imaginando",
        "Coletando recursos",
        "Elaborando",
        "Refletindo",
        "Processando",
        "Organizando ideias",
        "Consultando o oráculo",
        "Filosofando",
        "Ruminando"
    )
    ```

- **DEEP_SUBTOPICS**: Number of subtopics to drill into in deep research mode.
  - *Type*: `int`
  - *Value*: `4`

- **DEEP_FETCH_TOP**: Top links to fetch full text from per research pass.
  - *Type*: `int`
  - *Value*: `2`
