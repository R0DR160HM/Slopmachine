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
import ast
import html
import itertools
import json
import msvcrt
import operator
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime
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
_term_state: dict = {"buf": [], "active": False, "status": "", "nlines": 2}
_PROMPT_CORE = "\033[1;34mDigite: \033[0m"


def _build_prompt_block() -> tuple[str, int]:
    """Return (text, line_count) for the bottom input area.

    When a status line is set (e.g. the live "Pensando..." timer), it is drawn
    just above the "Digite:" prompt; otherwise the prompt keeps its usual
    single blank line above it.
    """
    buf = "".join(_term_state["buf"])
    status = _term_state.get("status") or ""
    if status:
        return f"\n{status}\n{_PROMPT_CORE}{buf}", 3
    return f"\n{_PROMPT_CORE}{buf}", 2


def _erase_prompt_block() -> None:
    """Erase the currently-drawn prompt block (cursor ends where it started)."""
    n = _term_state.get("nlines", 2)
    sys.stdout.write("\r\033[2K")
    for _ in range(n - 1):
        sys.stdout.write("\033[1A\033[2K")


def _draw_prompt_block() -> None:
    """Draw the prompt block and remember how many lines it occupies."""
    block, n = _build_prompt_block()
    sys.stdout.write(block)
    _term_state["nlines"] = n
    sys.stdout.flush()


def _set_status(text: str) -> None:
    """Update the live status line shown above the prompt, redrawing in place."""
    with _term_lock:
        _term_state["status"] = text
        if _term_state["active"]:
            _erase_prompt_block()
            _draw_prompt_block()


def _safe_write(text: str) -> None:
    """Write raw text to stdout, managing the input-prompt area."""
    with _term_lock:
        if _term_state["active"]:
            _erase_prompt_block()
        sys.stdout.write(text)
        sys.stdout.flush()
        if _term_state["active"]:
            _draw_prompt_block()


class SafeConsole(Console):
    """Rich Console whose print() erases/restores the msvcrt input prompt."""

    def print(self, *args, **kwargs) -> None:  # type: ignore[override]
        with _term_lock:
            if _term_state["active"]:
                _erase_prompt_block()
            super().print(*args, **kwargs)
            if _term_state["active"]:
                _draw_prompt_block()


console = SafeConsole()

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "qwen2.5:3b"
DEFAULT_MAX_RESULTS = 5

# Context window (tokens) sent to Ollama. Set explicitly so behaviour is
# predictable instead of relying on Ollama's small default (~2048-4096).
# qwen2.5:3b supports up to 32k; 30k leaves headroom for the model's reply.
NUM_CTX = 30000

# Char budget for the conversation we send each turn. Roughly NUM_CTX * 4 chars
# per token, minus headroom for the model's own reply. Older turns beyond this
# are dropped — but the system prompt is always kept (see trim_messages).
HISTORY_CHAR_BUDGET = 100000

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


def chat_with_timer(label: str, **chat_kwargs) -> Any:
    """Run ollama.chat in a worker thread while showing a live elapsed timer.

    The timer is rendered on the status line just above the input prompt, e.g.
    "Pensando... (3s)", updated once per second until the model responds.
    """
    result: dict[str, Any] = {}

    def _worker() -> None:
        try:
            result["value"] = ollama.chat(**chat_kwargs)
        except BaseException as exc:  # re-raised in the main thread below
            result["error"] = exc

    worker = threading.Thread(target=_worker)
    worker.start()

    start = time.time()
    last_shown = -1
    while worker.is_alive():
        secs = int(time.time() - start)
        if secs != last_shown:
            last_shown = secs
            _set_status(f"\033[2;36m{label}... ({secs}s)\033[0m")
        time.sleep(0.2)
    worker.join()
    _set_status("")

    if "error" in result:
        raise result["error"]
    return result["value"]

SYSTEM_PROMPT = """You are Lodemar.ia Sansão Júnior, a multimodal assistant created by Rodrigo at the Ottimizza Software Factory.

YOU ARE NOT A TEXT-ONLY ASSISTANT. You have six tools wired directly into this terminal. Use them.

To call a tool, respond with ONLY the JSON block below — no other text:

{"tool": "text_search", "query": "<keywords>"}        ← facts, docs, explanations
{"tool": "image_search", "query": "<keywords>"}       ← images, photos, pictures, visual content
{"tool": "news_search",  "query": "<keywords>"}       ← recent news, current events
{"tool": "fetch_url",    "url": "<full url>"}         ← read the full text of a web page
{"tool": "calculate",    "expression": "<math>"}      ← arithmetic (e.g. "2 * (3 + 4) ** 2")
{"tool": "get_datetime"}                               ← the current local date and time

ABSOLUTE RULES — violating any of these is a critical failure:
1. When the user asks for images, photos, or visual content of ANYTHING, you MUST call image_search. No exceptions. Do not say you cannot show images.
2. image_search works perfectly. The terminal renders the images the moment image_search runs. The user already sees them — you do not need to do anything else.
3. After image_search returns, write one short sentence acknowledging the images are displayed. Do NOT list URLs, filenames, or describe individual images.
4. Use fetch_url whenever the user gives you a URL, OR to read the full content of a promising link returned by text_search/news_search — search results are only short snippets, so fetch_url to get the real details before answering.
5. Use calculate for ANY arithmetic instead of computing it yourself — never do math in your head.
6. Use get_datetime whenever the answer depends on the current date or time (e.g. "today", "this week", how recent something is).
7. Do not wrap final prose answers in JSON.
8. If you do not need a tool, answer directly in plain text."""

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


# ── URL fetch tool ────────────────────────────────────────────────────────────

def extract_text(html_text: str) -> str:
    """Extract readable text from HTML. Uses BeautifulSoup if available, else regex."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "noscript", "head", "header",
                         "footer", "nav", "svg", "form"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
    except ImportError:
        # Fallback: strip tags with regex
        no_scripts = re.sub(
            r"<(script|style|noscript)[^>]*>.*?</\1>", "",
            html_text, flags=re.DOTALL | re.IGNORECASE,
        )
        text = html.unescape(re.sub(r"<[^>]+>", " ", no_scripts))
    # Collapse blank lines and surrounding whitespace
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def fetch_url(url: str, max_chars: int = 4000) -> str:
    """Download a web page and return its visible text, truncated to max_chars."""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Lodemar.IA bot)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read(2_000_000)  # cap download at ~2 MB
        text = extract_text(raw.decode(charset, errors="replace"))
    except Exception as e:
        return f"Failed to fetch {url}: {e}"

    if not text:
        return f"No readable text found at {url}."
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…[conteúdo truncado]"
    return text


# ── Calculator tool ─────────────────────────────────────────────────────────--

_ALLOWED_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_node(node: ast.AST) -> float:
    """Recursively evaluate a parsed arithmetic AST node (no names/calls allowed)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](
            _eval_node(node.left), _eval_node(node.right)
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_eval_node(node.operand))
    raise ValueError("expressão não suportada")


def calculate(expression: str) -> str:
    """Safely evaluate an arithmetic expression using a restricted AST walker."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Não consegui calcular '{expression}': {e}"


# ── Date/time tool ────────────────────────────────────────────────────────────

def get_datetime() -> str:
    """Return the current local date and time as a readable string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")


# ── Tool-call detection ───────────────────────────────────────────────────────

# Tool name → tuple of required JSON keys (empty tuple = no arguments needed).
_VALID_TOOLS: dict[str, tuple[str, ...]] = {
    "text_search":  ("query",),
    "image_search": ("query",),
    "news_search":  ("query",),
    "fetch_url":    ("url",),
    "calculate":    ("expression",),
    "get_datetime": (),
}


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
    except json.JSONDecodeError:
        return None
    tool = data.get("tool")
    if tool in _VALID_TOOLS and all(k in data for k in _VALID_TOOLS[tool]):
        return data
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


# ── History trimming ──────────────────────────────────────────────────────────

def trim_messages(
    messages: list[dict[str, str]], max_chars: int = HISTORY_CHAR_BUDGET
) -> list[dict[str, str]]:
    """
    Return a view of `messages` that fits within `max_chars`, used only for what
    we send to the model (the full history stays in `messages` for now).

    The system prompt (messages[0]) is ALWAYS preserved, so when the context
    window fills up the model never loses its identity or tool instructions —
    we drop the oldest *conversation* turns instead. The most recent turn (the
    latest tool result the model needs to answer) is kept first.
    """
    if len(messages) <= 1:
        return messages

    system, rest = messages[0], messages[1:]
    total = len(system["content"])
    kept: list[dict[str, str]] = []
    # Walk newest → oldest, keeping turns until the budget runs out.
    for msg in reversed(rest):
        size = len(msg["content"])
        if kept and total + size > max_chars:
            break
        total += size
        kept.append(msg)
    kept.reverse()
    return [system] + kept


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

    active_model = model  # may be upgraded to Megabrain mid-session
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
                _draw_prompt_block()
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

        # Megabrain trigger
        if re.search(r"mega\s*brain", user_input, re.IGNORECASE):
            active_model = "qwen2.5:7b"
            console.print("[bold magenta]⚡ Megabrain ativado.[/bold magenta]")
            messages.append({"role": "assistant", "content": "Megabrain ativado."})

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
            _prompt_gate.set()  # show "Digite:" now; SafeConsole keeps it below output
            response = chat_with_timer(
                next(_THINKING_LABELS),
                model=active_model,
                messages=trim_messages(messages),
                options={"num_thread": 8, "num_ctx": NUM_CTX},
            )
            assistant_text: str = response["message"]["content"]

            tool_call = parse_tool_call(assistant_text)

            if tool_call:
                tool = tool_call["tool"]
                query = tool_call.get("query", "")

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

                elif tool == "fetch_url":
                    url = tool_call["url"]
                    console.print(f"\n[bold yellow]🌐  Lendo página:[/bold yellow] [cyan]{url}[/cyan]")
                    page_text = fetch_url(url)
                    console.print(f"[dim]Extraí {len(page_text)} caractere(s) de {url}[/dim]\n")
                    feedback = f"Content fetched from {url}:\n\n{page_text}\n\nNow answer or make another tool call."

                elif tool == "calculate":
                    expression = tool_call["expression"]
                    console.print(f"\n[bold yellow]🧮  Calculando:[/bold yellow] [cyan]{expression}[/cyan]")
                    calc_result = calculate(expression)
                    console.print(f"[dim]{calc_result}[/dim]\n")
                    feedback = f"Calculation result: {calc_result}\n\nNow answer or make another tool call."

                elif tool == "get_datetime":
                    console.print("\n[bold yellow]🕐  Consultando data/hora atual[/bold yellow]")
                    now_str = get_datetime()
                    console.print(f"[dim]{now_str}[/dim]\n")
                    feedback = f"Current local date and time: {now_str}\n\nNow answer or make another tool call."

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
