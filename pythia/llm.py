"""Helpers for talking to the Ollama model and managing message history."""

import json
import queue
import re
import threading
import time
from typing import Iterator

import ollama

from pythia.config import (
    EMBED_MODEL,
    HISTORY_CHAR_BUDGET,
    OLLAMA_OPTIONS,
    STREAM_LOOP_WINDOW_LINES,
)
from pythia.terminal import console, prompt_area

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_TAG = "<think>"

Message = dict[str, str]

_DONE = object()


def strip_think(text: str) -> str:
    """Remove <think>...</think> blocks (Qwen3 thinking mode)."""
    return _THINK_RE.sub("", text).strip()


def visible_text(partial: str) -> str:
    """The portion of a partially-received response that is safe to display.

    Completed <think>...</think> blocks are removed; everything after an
    unclosed <think> is hidden, as is a partially-received "<think" tag at
    the very end of the text.
    """
    text = _THINK_RE.sub("", partial)
    open_idx = text.find(_THINK_TAG)
    if open_idx != -1:
        return text[:open_idx]
    for i in range(len(_THINK_TAG) - 1, 0, -1):
        if text.endswith(_THINK_TAG[:i]):
            return text[:-i]
    return text


# ── Lazy model installation ────────────────────────────────────────────────────
# No model is downloaded up front: every call simply runs, and only when the
# server answers "model not found" is the model pulled and the call retried.

def _is_missing_model_error(exc: BaseException) -> bool:
    """True for the Ollama error that means the model is not installed."""
    if isinstance(exc, ollama.ResponseError):
        text = str(getattr(exc, "error", "") or exc).lower()
        return getattr(exc, "status_code", None) == 404 or "not found" in text
    return False


def pull_model(model: str) -> None:
    """Download one model now, streaming its progress on the status line."""
    console.print(
        f"[yellow]⬇️  Modelo '{model}' não está instalado — baixando...[/yellow]"
    )
    try:
        for part in ollama.pull(model=model, stream=True):
            get = part.get if isinstance(part, dict) else (
                lambda key, part=part: getattr(part, key, None)
            )
            completed, total = get("completed"), get("total")
            if completed and total:
                detail = f"{completed * 100 // total}%"
            else:
                detail = str(get("status") or "...")
            prompt_area.set_status(f"\033[2;36m⬇️  {model}: {detail}\033[0m")
    finally:
        prompt_area.set_status("")
    console.print(f"[dim]Modelo '{model}' instalado.[/dim]")


def _call_pulling_model(model: str, call):
    """Run `call()`; when it fails because `model` is not installed, pull the
    model and run it once more."""
    try:
        return call()
    except Exception as e:
        if not _is_missing_model_error(e):
            raise
        pull_model(model)
        return call()


# List markers ("3.", "b)", "-", "*", "•") and digits are exactly what a
# looping model varies between otherwise-identical lines, so both are erased
# before lines are compared.
_LIST_PREFIX_RE = re.compile(r"^\s*(?:\d+[.):]|[a-zA-Z][.)]|[-*•+])\s+")
_DIGITS_RE = re.compile(r"\d+")

# A canonical-match loop verdict needs at least this many letters across the
# window: with digits erased, tables of numbers (`| 2021 | 15 |` rows) all
# canonicalize alike, and this keeps them from reading as a loop.
_LOOP_MIN_LETTERS = 20


def _canon_line(line: str) -> str:
    """A line reduced to what a repetition loop keeps constant: list markers
    and numbers erased, whitespace collapsed, case folded."""
    line = _LIST_PREFIX_RE.sub("", line)
    line = _DIGITS_RE.sub("#", line)
    return " ".join(line.split()).lower()


def _strip_stream_loop(raw: str) -> str | None:
    """Repetition-loop detection on a partially streamed response: when the
    last STREAM_LOOP_WINDOW_LINES complete lines already appeared earlier in
    the same text — verbatim, or up to renumbering/bullet churn (see
    _canon_line) — the model is looping. Returns `raw` with that repeated
    tail (and the partial line after it) removed — or None when there is no
    loop and streaming should continue."""
    lines = raw.split("\n")
    complete = lines[:-1]  # the last element is a partial line, still coming
    window = STREAM_LOOP_WINDOW_LINES
    if len(complete) < window:
        return None
    tail = "\n".join(complete[-window:])
    if not tail.strip():
        return None  # a run of blank lines is spacing, not a loop
    truncated = "\n".join(complete[:-window])
    if raw.count(tail) >= 2:  # the tail also appears verbatim earlier
        return truncated
    # Near-duplicate loops (only the list numbers change, say) escape the
    # verbatim match — compare canonicalized lines instead.
    canon = [_canon_line(line) for line in complete]
    canon_tail = canon[-window:]
    if sum(ch.isalpha() for ch in "".join(canon_tail)) < _LOOP_MIN_LETTERS:
        return None
    for i in range(len(canon) - window):
        if canon[i : i + window] == canon_tail:
            return truncated
    return None


def stream_chat(label: str, **chat_kwargs) -> Iterator[str]:
    """Stream ollama.chat, yielding the accumulated raw text as tokens arrive.

    When the model is not installed yet (the server answers "not found" —
    always before the first token), it is pulled and the request restarted.

    The request runs in a worker thread so that, between tokens, a live
    elapsed timer is rendered on the status line just above the input prompt,
    e.g. "Pensando... (3s)". The last yielded value is the complete response.
    Errors from the worker are re-raised in the calling thread.
    """
    for attempt in (1, 2):
        try:
            yield from _stream_chat_once(label, **chat_kwargs)
            return
        except Exception as e:
            if attempt == 1 and _is_missing_model_error(e):
                pull_model(str(chat_kwargs.get("model")))
                continue
            raise


def _stream_chat_once(label: str, **chat_kwargs) -> Iterator[str]:
    tokens: queue.Queue = queue.Queue()
    chat_kwargs.setdefault("think", False)
    stop = threading.Event()  # set to abort the generation server-side

    def _worker() -> None:
        try:
            for chunk in ollama.chat(stream=True, **chat_kwargs):
                tokens.put(chunk["message"]["content"])
                if stop.is_set():
                    break  # closes the stream; the server stops generating
            tokens.put(_DONE)
        except BaseException as exc:  # re-raised in the calling thread below
            tokens.put(exc)

    threading.Thread(target=_worker, daemon=True).start()

    raw = ""
    start = time.time()
    last_shown = -1
    try:
        while True:
            secs = int(time.time() - start)
            if secs != last_shown:
                last_shown = secs
                prompt_area.set_status(f"\033[2;36m{label}... ({secs}s)\033[0m")
            try:
                item = tokens.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is _DONE:
                return
            if isinstance(item, BaseException):
                raise item
            if item:
                raw += item
                # Only a chunk that completes a line can close a loop window.
                if "\n" in item:
                    truncated = _strip_stream_loop(raw)
                    if truncated is not None:
                        stop.set()
                        console.print(
                            "[dim]🔁  Loop de repetição detectado — resposta "
                            "interrompida.[/dim]"
                        )
                        yield truncated
                        return
                yield raw
    finally:
        stop.set()  # a consumer that bails early also stops the generation
        prompt_area.set_status("")


def ask(model: str, system: str, user: str, label: str) -> str:
    """One-shot model call (fresh context) returning cleaned plain text."""
    raw = ""
    for raw in stream_chat(
        label,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options=OLLAMA_OPTIONS,
    ):
        pass
    return strip_think(raw)


# EmbeddingGemma is trained with task-specific prompts: document chunks and
# search queries must be embedded with different prefixes for retrieval to
# work well (see the model card).
_EMBED_DOC_PREFIX = "title: none | text: "
_EMBED_QUERY_PREFIX = "task: search result | query: "


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embedding vectors for document chunks (the indexing side of search)."""
    response = _call_pulling_model(EMBED_MODEL, lambda: ollama.embed(
        model=EMBED_MODEL, input=[_EMBED_DOC_PREFIX + t for t in texts]
    ))
    return [list(v) for v in response["embeddings"]]


def embed_query(text: str) -> list[float]:
    """Embedding vector for one search query."""
    response = _call_pulling_model(EMBED_MODEL, lambda: ollama.embed(
        model=EMBED_MODEL, input=[_EMBED_QUERY_PREFIX + text]
    ))
    return list(response["embeddings"][0])


def trim_messages(
    messages: list[Message], max_chars: int = HISTORY_CHAR_BUDGET
) -> list[Message]:
    """Return a view of `messages` that fits within `max_chars`, used only for
    what we send to the model (the full history stays in `messages`).

    The system prompt (messages[0]) is ALWAYS preserved, so when the context
    window fills up the model never loses its identity or tool instructions —
    we drop the oldest *conversation* turns instead. The most recent turn (the
    latest tool result the model needs to answer) is kept first.
    """
    if len(messages) <= 1:
        return messages

    system, rest = messages[0], messages[1:]
    total = len(system["content"])
    kept: list[Message] = []
    # Walk newest → oldest, keeping turns until the budget runs out.
    for msg in reversed(rest):
        size = len(msg["content"])
        if kept and total + size > max_chars:
            break
        total += size
        kept.append(msg)
    kept.reverse()
    return [system] + kept


def parse_list(text: str, limit: int) -> list[str]:
    """Extract a list of short strings from a model reply (JSON array or lines)."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            items = json.loads(match.group())
            if isinstance(items, list):
                out = [str(x).strip() for x in items if str(x).strip()]
                if out:
                    return out[:limit]
        except json.JSONDecodeError:
            pass
    # Fallback: strip bullets/numbering from each non-empty line
    lines = []
    for ln in text.splitlines():
        ln = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", ln).strip()
        if ln:
            lines.append(ln)
    return lines[:limit]
