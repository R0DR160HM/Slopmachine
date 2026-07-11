"""tool_forge: have a coder model write a brand-new tool at runtime.

The coder model (config.FORGE_MODEL) receives the agent's description of the
desired tool and must answer with a Python module defining TOOL_NAME,
TOOL_DESCRIPTION and run(input: str) -> str. The module is loaded here and
handed back to the tool registry, which makes it callable by the agent.

The generated code is shown to the user (syntax-highlighted) before it is
loaded, and it executes with full local privileges — same trust level as the
rest of this app.
"""

import re
from dataclasses import dataclass
from typing import Callable

from pythia import config
from pythia.config import OLLAMA_OPTIONS
from pythia.llm import strip_think
from pythia.prompts import FORGE_SYSTEM_PROMPT
from pythia.streaming import stream_markdown

_CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)
_NAME_CLEAN_RE = re.compile(r"[^a-z0-9_]+")


class ForgeError(Exception):
    """The coder model failed to produce a loadable tool."""


@dataclass
class ForgedTool:
    name: str
    description: str
    run: Callable[[str], str]
    code: str


def _extract_code(text: str) -> str:
    match = _CODE_BLOCK_RE.search(text)
    if match:
        return match.group(1).strip()
    # No fence — accept the raw text if it plausibly is the module itself
    if "def run" in text:
        return text.strip()
    raise ForgeError("a resposta do modelo não contém um bloco de código Python")


def _normalize_name(raw_name: object) -> str:
    name = _NAME_CLEAN_RE.sub("_", str(raw_name).strip().lower()).strip("_")
    return name or "forged_tool"


def forge_tool(description: str) -> ForgedTool:
    """Ask the coder model to build the described tool; load and return it.

    The generation streams live in the terminal. Raises ForgeError when the
    response has no code block, the code fails to load, or the run()/TOOL_NAME
    contract is not met.
    """
    raw = stream_markdown(
        "Forjando ferramenta",
        model=config.FORGE_MODEL,
        messages=[
            {"role": "system", "content": FORGE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Tool request: {description}"},
        ],
        options=OLLAMA_OPTIONS,
    )
    code = _extract_code(strip_think(raw))

    namespace: dict = {}
    try:
        exec(compile(code, "<forged_tool>", "exec"), namespace)
    except Exception as e:
        raise ForgeError(f"o código gerado falhou ao carregar: {e}") from e

    run = namespace.get("run")
    if not callable(run):
        raise ForgeError("o código gerado não define uma função run()")

    return ForgedTool(
        name=_normalize_name(namespace.get("TOOL_NAME", "forged_tool")),
        description=str(namespace.get("TOOL_DESCRIPTION", description)).strip(),
        run=run,
        code=code,
    )
