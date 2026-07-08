"""Detection and execution of tool calls emitted by the model."""

import json
import re
from typing import Any, Callable

from rich.panel import Panel
from rich.syntax import Syntax

from lodemaria.config import FORGED_RESULT_MAX_CHARS
from lodemaria.llm import strip_think
from lodemaria.terminal import console
from lodemaria.tools.calculator import calculate
from lodemaria.tools.display import display_images
from lodemaria.tools.forge import ForgedTool, ForgeError, forge_tool
from lodemaria.tools.search import (
    format_image_results,
    format_news_results,
    format_search_results,
    image_search,
    news_search,
    web_search,
)
from lodemaria.tools.webpage import fetch_url

# Tool name → tuple of required JSON keys.
_REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "web_search": ("query",),
    "image_search": ("query",),
    "news_search": ("query",),
    "fetch_url": ("url",),
    "calculate": ("expression",),
    "tool_forge": ("expression",),
}

# Tools forged at runtime, keyed by name. They take a single "input" string
# (optional in the call — a missing key means empty input, since small models
# often drop it).
_forged_tools: dict[str, ForgedTool] = {}

_JSON_OBJECT_RE = re.compile(r"\{.*?\}", re.DOTALL)


def parse_tool_call(text: str) -> dict[str, Any] | None:
    """Return the parsed JSON dict if the model emitted a tool call,
    or None if it's a plain text answer.
    Handles optional <think>...</think> blocks (Qwen3 thinking mode).
    """
    # Look for a JSON object anywhere in the (cleaned) response
    match = _JSON_OBJECT_RE.search(strip_think(text))
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    tool = data.get("tool")
    if tool in _forged_tools:
        return data
    if tool in _REQUIRED_KEYS and all(k in data for k in _REQUIRED_KEYS[tool]):
        return data
    return None


def _run_web_search(call: dict, max_results: int) -> str:
    query = call["query"]
    console.print(f"\n[bold yellow]🔍  Pesquisando:[/bold yellow] [cyan]{query}[/cyan]")
    results = web_search(query, max_results=max_results)
    console.print(f"[dim]Encontrei {len(results)} resultado(s)[/dim]\n")
    return (
        f"Search results for '{query}':\n\n{format_search_results(results)}\n\n"
        "Now answer or make another tool call."
    )


def _run_image_search(call: dict, max_results: int) -> str:
    query = call["query"]
    console.print(f"\n[bold yellow]🖼️   Buscando imagens:[/bold yellow] [cyan]{query}[/cyan]")
    results = image_search(query, max_results=max_results)
    console.print(f"[dim]Encontrei {len(results)} imagem(ns)[/dim]")
    display_images(results)
    return (
        f"Image search results for '{query}':\n\n{format_image_results(results)}\n\n"
        "Images were displayed to the user. Now answer or make another tool call."
    )


def _run_news_search(call: dict, max_results: int) -> str:
    query = call["query"]
    console.print(f"\n[bold yellow]📰  Buscando notícias:[/bold yellow] [cyan]{query}[/cyan]")
    results = news_search(query, max_results=max_results)
    console.print(f"[dim]Encontrei {len(results)} notícia(s)[/dim]\n")
    return (
        f"News results for '{query}':\n\n{format_news_results(results)}\n\n"
        "Now answer or make another tool call."
    )


def _run_fetch_url(call: dict, max_results: int) -> str:
    url = call["url"]
    console.print(f"\n[bold yellow]🌐  Lendo página:[/bold yellow] [cyan]{url}[/cyan]")
    page_text = fetch_url(url)
    console.print(f"[dim]Extraí {len(page_text)} caractere(s) de {url}[/dim]\n")
    return (
        f"Content fetched from {url}:\n\n{page_text}\n\n"
        "Now answer or make another tool call."
    )


def _run_calculate(call: dict, max_results: int) -> str:
    expression = call["expression"]
    console.print(f"\n[bold yellow]🧮  Calculando:[/bold yellow] [cyan]{expression}[/cyan]")
    result = calculate(expression)
    console.print(f"[dim]{result}[/dim]\n")
    return f"Calculation result: {result}\n\nNow answer or make another tool call."


def _run_tool_forge(call: dict, max_results: int) -> str:
    description = call["expression"]
    console.print(f"\n[bold yellow]🛠️   Forjando ferramenta:[/bold yellow] [cyan]{description}[/cyan]")
    try:
        tool = forge_tool(description)
    except ForgeError as e:
        console.print(f"[red]Falha ao forjar a ferramenta: {e}[/red]\n")
        return (
            f"tool_forge failed: {e}\n\n"
            "Retry with a clearer description, use another tool, or answer directly."
        )

    # Never let a forged tool shadow a built-in one
    while tool.name in _REQUIRED_KEYS:
        tool.name = f"forged_{tool.name}"
    _forged_tools[tool.name] = tool

    console.print(Panel(
        Syntax(tool.code, "python", word_wrap=True),
        title=f"🛠️  {tool.name}",
        subtitle=tool.description,
        border_style="yellow",
    ))
    console.print(f"[dim]Ferramenta '{tool.name}' pronta para uso.[/dim]\n")
    return (
        f"Tool '{tool.name}' was created and is now available.\n"
        f"Description: {tool.description}\n"
        f'To use it, respond with ONLY this JSON: {{"tool": "{tool.name}", "input": "<input string>"}}\n'
        "It takes a single string input and returns a string.\n"
        "Now call the new tool, make another tool call, or answer directly."
    )


def _run_forged_tool(call: dict, max_results: int) -> str:
    tool = _forged_tools[call["tool"]]
    argument = str(call.get("input", ""))
    console.print(f"\n[bold yellow]🧩  Executando '{tool.name}':[/bold yellow] [cyan]{argument}[/cyan]")
    try:
        result = str(tool.run(argument))
    except Exception as e:
        result = f"Tool '{tool.name}' raised an error: {e}"
    if len(result) > FORGED_RESULT_MAX_CHARS:
        result = result[:FORGED_RESULT_MAX_CHARS] + "\n…[saída truncada]"
    console.print(f"[dim]{result}[/dim]\n")
    return (
        f"Result from tool '{tool.name}' for input '{argument}':\n\n{result}\n\n"
        "Now answer or make another tool call."
    )


_HANDLERS: dict[str, Callable[[dict, int], str]] = {
    "web_search": _run_web_search,
    "image_search": _run_image_search,
    "news_search": _run_news_search,
    "fetch_url": _run_fetch_url,
    "calculate": _run_calculate,
    "tool_forge": _run_tool_forge,
}


def execute_tool_call(call: dict[str, Any], max_results: int) -> str:
    """Run a parsed tool call and return the feedback message for the model."""
    handler = _HANDLERS.get(call["tool"], _run_forged_tool)
    return handler(call, max_results)
