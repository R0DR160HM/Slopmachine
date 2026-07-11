"""Helpers for talking to the Ollama model and managing message history."""

import json
import queue
import re
import threading
import time
from typing import Iterator

import ollama

from lodemaria.config import HISTORY_CHAR_BUDGET, OLLAMA_OPTIONS
from lodemaria.terminal import prompt_area

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


def stream_chat(label: str, **chat_kwargs) -> Iterator[str]:
    """Stream ollama.chat, yielding the accumulated raw text as tokens arrive.

    The request runs in a worker thread so that, between tokens, a live
    elapsed timer is rendered on the status line just above the input prompt,
    e.g. "Pensando... (3s)". The last yielded value is the complete response.
    Errors from the worker are re-raised in the calling thread.
    """
    tokens: queue.Queue = queue.Queue()

    def _worker() -> None:
        try:
            for chunk in ollama.chat(stream=True, **chat_kwargs):
                tokens.put(chunk["message"]["content"])
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
                yield raw
    finally:
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
