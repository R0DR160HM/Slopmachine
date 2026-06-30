"""
ollama_search.py
────────────────
Chat with an Ollama model that can search the web via DuckDuckGo (ddgs).

Requirements:
    pip install ddgs ollama rich

Usage:
    python ollama_search.py
    python ollama_search.py --model qwen3.5:4b --results 5
"""

import argparse
import itertools
import json
import msvcrt
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from typing import Any

import ollama
from ddgs import DDGS
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# ── Thread-safe terminal input state ─────────────────────────────────────────
# _term_lock guards both the input buffer and any stdout writes so that
# concurrent console.print() calls erase the "Digite:" line, print their
# content, then redraw the prompt — keeping it always at the bottom.

_term_lock = threading.Lock()
_term_state: dict = {"buf": [], "active": False}
_PROMPT_STR = "\n\033[1;34mDigite: \033[0m"


def _safe_write(text: str) -> None:
    """Write raw text to stdout, managing the input-prompt area."""
    with _term_lock:
        if _term_state["active"]:
            sys.stdout.write("\r\033[2K\033[1A\033[2K")
            sys.stdout.flush()
        sys.stdout.write(text)
        sys.stdout.flush()
        if _term_state["active"]:
            sys.stdout.write(_PROMPT_STR + "".join(_term_state["buf"]))
            sys.stdout.flush()


class SafeConsole(Console):
    """Rich Console whose print() erases/restores the msvcrt input prompt."""

    def print(self, *args, **kwargs) -> None:  # type: ignore[override]
        with _term_lock:
            if _term_state["active"]:
                sys.stdout.write("\r\033[2K\033[1A\033[2K")
                sys.stdout.flush()
            super().print(*args, **kwargs)
            if _term_state["active"]:
                sys.stdout.write(_PROMPT_STR + "".join(_term_state["buf"]))
                sys.stdout.flush()


console = SafeConsole()

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "qwen2.5:3b"
DEFAULT_MAX_RESULTS = 5

_THINKING_LABELS = itertools.cycle([
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
])

SYSTEM_PROMPT = """You are Lodemar.ia Sansão Júnior, a multimodal assistant created by Rodrigo at the Ottimizza Software Factory.

YOU ARE NOT A TEXT-ONLY ASSISTANT. You have three tools wired directly into this terminal. Use them.

To call a tool, respond with ONLY the JSON block below — no other text:

{"tool": "text_search", "query": "<keywords>"}      ← facts, docs, explanations
{"tool": "image_search", "query": "<keywords>"}     ← images, photos, pictures, visual content
{"tool": "news_search",  "query": "<keywords>"}     ← recent news, current events

ABSOLUTE RULES — violating any of these is a critical failure:
1. When the user asks for images, photos, or visual content of ANYTHING, you MUST call image_search. No exceptions. Do not say you cannot show images.
2. image_search works perfectly. The terminal renders the images the moment image_search runs. The user already sees them — you do not need to do anything else.
3. After image_search returns, write one short sentence acknowledging the images are displayed. Do NOT list URLs, filenames, or describe individual images.
4. Do not wrap final prose answers in JSON.
5. If you do not need a tool, answer directly in plain text."""

# ── Search tool ───────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict[str, str]]:
    """Run a DuckDuckGo text search and return a list of result dicts."""
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
    return results or []


def format_search_results(results: list[dict[str, str]]) -> str:
    """Format search results into a readable block for the model."""
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        body  = r.get("body", "No snippet")
        href  = r.get("href", "")
        lines.append(f"[{i}] {title}\n    {body}\n    URL: {href}")
    return "\n\n".join(lines)


def image_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    """Run a DuckDuckGo image search and return a list of result dicts."""
    with DDGS() as ddgs:
        results = ddgs.images(query, max_results=max_results)
    return results or []


def news_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    """Run a DuckDuckGo news search and return a list of result dicts."""
    with DDGS() as ddgs:
        results = ddgs.news(query, max_results=max_results)
    return results or []


def format_image_results(results: list[dict]) -> str:
    """Format image results as text context for the model."""
    if not results:
        return "No images found."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        image_url = r.get("image", "")
        source = r.get("url", "")
        w, h = r.get("width", "?"), r.get("height", "?")
        lines.append(f"[{i}] {title} ({w}x{h})\n    Image: {image_url}\n    Source: {source}")
    return "\n\n".join(lines)


def format_news_results(results: list[dict]) -> str:
    """Format news results into a readable block for the model."""
    if not results:
        return "No news found."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        body = r.get("body", "No snippet")
        url = r.get("url", "")
        date = r.get("date", "")
        source = r.get("source", "")
        lines.append(f"[{i}] {title}\n    {source} · {date}\n    {body}\n    URL: {url}")
    return "\n\n".join(lines)


def display_images(results: list[dict], max_display: int = 3) -> None:
    """Render top image results side-by-side as Unicode half-block art (24-bit ANSI)."""
    try:
        from PIL import Image as PilImage
    except ImportError:
        console.print("[dim]  (pillow não encontrado — pip install pillow)[/dim]")
        return

    # Download all images into memory before rendering
    panels: list[tuple[list, str]] = []
    for r in results:
        if len(panels) >= max_display:
            break
        url = r.get("thumbnail") or r.get("image")
        title = r.get("title", "")
        if not url:
            continue
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                tmp = f.name
            urllib.request.urlretrieve(url, tmp)
            img = PilImage.open(tmp).convert("RGB")
            img.load()
            panels.append((img, title))
        except Exception:
            pass
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

    if not panels:
        return

    # Compute per-image width so all images fit side by side
    n = len(panels)
    gap = 2
    try:
        term_w = os.get_terminal_size().columns - 2
    except OSError:
        term_w = 118
    img_w = (term_w - gap * (n - 1)) // n
    img_h = 30  # character rows (each covers 2 pixel rows)

    # Resize all images to the same dimensions and extract pixels
    resized: list[tuple[list, str]] = []
    for img, title in panels:
        raw = img.resize((img_w, img_h * 2), PilImage.LANCZOS).tobytes()
        px = [raw[i:i+3] for i in range(0, len(raw), 3)]
        resized.append((px, title))

    # Titles line
    title_line = (" " * gap).join(t[:img_w].ljust(img_w) for _, t in resized)
    console.print(f"[dim]  {title_line}[/dim]")

    # Render row by row across all images simultaneously
    gap_str = "\x1b[0m" + " " * gap
    for row in range(0, img_h * 2 - 1, 2):
        line = ""
        for i, (px, _) in enumerate(resized):
            if i:
                line += gap_str
            for col in range(img_w):
                t = px[row * img_w + col]
                b = px[(row + 1) * img_w + col]
                line += (
                    f"\x1b[38;2;{t[0]};{t[1]};{t[2]}m"
                    f"\x1b[48;2;{b[0]};{b[1]};{b[2]}m▀"
                )
        _safe_write(line + "\x1b[0m\n")
    _safe_write("\n")


# ── Tool-call detection ───────────────────────────────────────────────────────

def parse_tool_call(text: str) -> dict[str, Any] | None:
    """
    Return the parsed JSON dict if the model emitted a tool call,
    or None if it's a plain text answer.
    Handles optional <think>...</think> blocks (Qwen3 thinking mode).
    """
    # Strip optional <think>...</think> reasoning block
    clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Look for a JSON object anywhere in the (cleaned) response
    match = re.search(r"\{.*?\}", clean, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        if data.get("tool") in {"text_search", "image_search", "news_search"} and "query" in data:
            return data
    except json.JSONDecodeError:
        pass
    return None


def strip_think(text: str) -> str:
    """Remove <think>...</think> blocks before printing to the user."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


# ── Pre-search for bracketed terms ───────────────────────────────────────────

def extract_bracket_terms(text: str) -> list[str]:
    """Return all terms enclosed in [square brackets] found in text."""
    return re.findall(r"\[([^\]]+)\]", text)


def pre_search_brackets(user_input: str, max_results: int) -> tuple[str, str]:
    """
    For each [term] in user_input, run web/image/news searches before the model.
    Image search triggers when the prompt contains "image".
    News search triggers when the prompt contains "news", "notícia", or "noticia".
    Returns (clean_prompt, search_context).
    """
    terms = extract_bracket_terms(user_input)
    if not terms:
        return user_input, ""

    clean_prompt = re.sub(r"\[([^\]]+)\]", r"\1", user_input)
    lower = user_input.lower()
    do_images = "image" in lower
    do_news = any(w in lower for w in ("news", "notícia", "noticia"))

    sections: list[str] = []
    for term in terms:
        # Text search (always)
        console.print(f"\n[bold yellow]🔍  Pesquisando:[/bold yellow] [cyan]{term}[/cyan]")
        text_results = web_search(term, max_results=max_results)
        console.print(f"[dim]Encontrei {len(text_results)} resultado(s) de texto para '{term}'[/dim]")
        sections.append(f"=== Resultados de texto para '{term}' ===\n{format_search_results(text_results)}")

        # Image search
        if do_images:
            console.print(f"[bold yellow]🖼️   Buscando imagens:[/bold yellow] [cyan]{term}[/cyan]")
            img_results = image_search(term, max_results=max_results)
            console.print(f"[dim]Encontrei {len(img_results)} imagem(ns) para '{term}'[/dim]")
            display_images(img_results)
            sections.append(f"=== Imagens para '{term}' ===\n{format_image_results(img_results)}")

        # News search
        if do_news:
            console.print(f"[bold yellow]📰  Buscando notícias:[/bold yellow] [cyan]{term}[/cyan]")
            news_results = news_search(term, max_results=max_results)
            console.print(f"[dim]Encontrei {len(news_results)} notícia(s) para '{term}'[/dim]")
            sections.append(f"=== Notícias para '{term}' ===\n{format_news_results(news_results)}")

    return clean_prompt, "\n\n".join(sections)


# ── Main chat loop ────────────────────────────────────────────────────────────

def chat(model: str, max_results: int) -> None:
    # Header
    console.clear()
    header = Text("🦙  Lodemar.IA Chat", style="bold cyan")
    console.print(Panel(header, expand=False, border_style="cyan"))
    console.print(f"[dim]Modelo:[/dim] [green]{model}[/green]  [dim]|  Digite[/dim] [yellow]quit[/yellow] [dim]ou[/dim] [yellow]exit[/yellow] [dim]para sair[/dim]\n")

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    msg_queue: queue.Queue[str | None] = queue.Queue()
    _prompt_gate = threading.Event()
    _prompt_gate.set()

    def _input_loop() -> None:
        """Character-by-character input via msvcrt; SafeConsole handles redraws."""
        while True:
            _prompt_gate.wait()
            _prompt_gate.clear()
            with _term_lock:
                _term_state["buf"] = []
                _term_state["active"] = True
                sys.stdout.write(_PROMPT_STR)
                sys.stdout.flush()
            while True:
                if not msvcrt.kbhit():
                    time.sleep(0.01)
                    continue
                ch = msvcrt.getwch()
                submit = False
                with _term_lock:
                    if ch == "\r":
                        _term_state["active"] = False
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        line = "".join(_term_state["buf"]).strip()
                        _term_state["buf"] = []
                        submit = True
                    elif ch in ("\x03", "\x04"):
                        _term_state["active"] = False
                        msg_queue.put(None)
                        return
                    elif ch == "\x08":
                        if _term_state["buf"]:
                            _term_state["buf"].pop()
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                    elif ch in ("\x00", "\xe0"):
                        if msvcrt.kbhit():
                            msvcrt.getwch()
                    elif ord(ch) >= 32:
                        _term_state["buf"].append(ch)
                        sys.stdout.write(ch)
                        sys.stdout.flush()
                if submit:
                    msg_queue.put(line)
                    if line.lower() in {"quit", "exit"}:
                        return
                    break

    threading.Thread(target=_input_loop, daemon=True).start()

    while True:
        user_input = msg_queue.get()

        if user_input is None:
            console.print("\n[dim]Até mais![/dim]")
            break
        if not user_input:
            _prompt_gate.set()
            continue
        if user_input.lower() in {"quit", "exit"}:
            console.print("[dim]Até mais![/dim]")
            break

        queued = msg_queue.qsize()
        if queued:
            s = "ns" if queued > 1 else ""
            console.print(f"[dim]({queued} mensagem{s} na fila)[/dim]")

        # Pre-search any [bracketed] terms before sending to the model
        clean_input, search_context = pre_search_brackets(user_input, max_results)

        if search_context:
            console.print()
            content = (
                f"Contexto de pesquisa prévia:\n\n{search_context}\n\n"
                f"Pergunta do usuário: {clean_input}"
            )
        else:
            content = user_input

        messages.append({"role": "user", "content": content})

        # Agentic loop: model may call the search tool before answering
        for attempt in range(10):          # guard against infinite loops
            console.print(f"\n[dim cyan]{next(_THINKING_LABELS)}...[/dim cyan]")
            _prompt_gate.set()  # show "Digite:" now; SafeConsole keeps it below output
            response = ollama.chat(model=model, messages=messages, options={"num_thread": 8})
            assistant_text: str = response["message"]["content"]

            tool_call = parse_tool_call(assistant_text)

            if tool_call:
                tool = tool_call["tool"]
                query = tool_call["query"]

                if tool == "image_search":
                    console.print(f"\n[bold yellow]🖼️   Buscando imagens:[/bold yellow] [cyan]{query}[/cyan]")
                    img_results = image_search(query, max_results=max_results)
                    console.print(f"[dim]Encontrei {len(img_results)} imagem(ns)[/dim]")
                    display_images(img_results)
                    result_text = format_image_results(img_results)
                    feedback = f"Image search results for '{query}':\n\n{result_text}\n\nImages were displayed to the user. Now answer or make another tool call."

                elif tool == "news_search":
                    console.print(f"\n[bold yellow]📰  Buscando notícias:[/bold yellow] [cyan]{query}[/cyan]")
                    news_results = news_search(query, max_results=max_results)
                    console.print(f"[dim]Encontrei {len(news_results)} notícia(s)[/dim]\n")
                    result_text = format_news_results(news_results)
                    feedback = f"News results for '{query}':\n\n{result_text}\n\nNow answer or make another tool call."

                else:  # "text_search"
                    console.print(f"\n[bold yellow]🔍  Pesquisando:[/bold yellow] [cyan]{query}[/cyan]")
                    results = web_search(query, max_results=max_results)
                    console.print(f"[dim]Encontrei {len(results)} resultado(s)[/dim]\n")
                    result_text = format_search_results(results)
                    feedback = f"Search results for '{query}':\n\n{result_text}\n\nNow answer or make another tool call."

                messages.append({"role": "assistant", "content": assistant_text})
                messages.append({"role": "user", "content": feedback})
            else:
                # Plain answer — done
                messages.append({"role": "assistant", "content": assistant_text})
                clean_response = strip_think(assistant_text)
                console.print(Panel(clean_response, title="[bold green]Júnior[/bold green]", border_style="green"))
                console.print()
                break
        else:
            console.print("[bold red]⚠️  Reached max tool-call iterations without a final answer.[/bold red]\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chat with an Ollama model that can search the web (ddgs)."
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--results", "-r",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Max search results per query (default: {DEFAULT_MAX_RESULTS})",
    )
    args = parser.parse_args()

    try:
        import ollama as _o  # noqa: F401
    except ImportError:
        sys.exit("❌  Missing dependency: pip install ollama")
    try:
        from ddgs import DDGS as _D  # noqa: F401
    except ImportError:
        sys.exit("❌  Missing dependency: pip install ddgs")
    try:
        import rich as _r  # noqa: F401
    except ImportError:
        sys.exit("❌  Missing dependency: pip install rich")
    ollama_proc = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)  # give the server a moment to start

    try:
        chat(model=args.model, max_results=args.results)
    finally:
        ollama_proc.terminate()
        try:
            ollama_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ollama_proc.kill()


if __name__ == "__main__":
    main()
