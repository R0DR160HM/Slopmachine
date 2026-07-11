"""Live token-by-token rendering of model responses.

The response streams into a transient rich Live region rendered as Markdown,
so the user watches the answer being written. When the response completes the
region is erased and the caller prints the definitive rendering — or nothing,
when the response turns out to be a tool call.

While the live region is on screen the bottom input prompt is hidden (the two
would fight over the same rows); keystrokes typed meanwhile keep accumulating
and reappear when the prompt is restored.
"""

import math

from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

from pythia.llm import stream_chat, visible_text
from pythia.terminal import console, prompt_area


def tail_view(text: str, width: int, max_rows: int) -> str:
    """The trailing portion of `text` that fits in ~max_rows rendered rows.

    A Live region cannot be taller than the terminal — rich truncates the
    bottom with "…", hiding exactly the newest streamed tokens. So once the
    content outgrows the screen we show a sliding window of its tail instead.
    Wrapped rows are estimated from line length; a ``` fence cut open by the
    crop is reopened so the visible tail still renders as markdown.
    """
    lines = text.splitlines()
    rows = 0
    start = len(lines)
    while start > 0:
        need = max(1, math.ceil(len(lines[start - 1]) / width))
        if rows + need > max_rows:
            break
        rows += need
        start -= 1
    if start == 0:
        return text
    if start == len(lines):  # a single line taller than the window — keep it
        start -= 1
    tail = lines[start:]
    dropped_fences = sum(1 for ln in lines[:start] if ln.lstrip().startswith("```"))
    if dropped_fences % 2:
        tail = ["```"] + tail
    return "\n".join(tail)


def stream_markdown(
    label: str,
    *,
    header: str | None = None,
    suppress_json: bool = False,
    **chat_kwargs,
) -> str:
    """Stream one chat response, rendering it live; return the raw full text.

    `header` (rich markup) is shown above the streaming text inside the
    transient region only — the caller prints the permanent version.

    With `suppress_json=True`, a response that opens with "{" or a code fence
    is kept off-screen (the "Pensando..." timer stays up instead): it is
    almost certainly a tool call, which is never displayed to the user.
    """
    raw = ""
    live = None
    try:
        for raw in stream_chat(label, **chat_kwargs):
            visible = visible_text(raw).strip()
            if not visible:
                continue
            if suppress_json and visible.startswith(("{", "```")):
                continue
            if live is None:
                prompt_area.hide()
                live = Live(
                    console=console,
                    transient=True,
                    refresh_per_second=8,
                    vertical_overflow="ellipsis",
                )
                live.start()
            # Keep the newest content on screen: crop to a tail that fits the
            # terminal (with margin for the header and markdown block spacing).
            width = max(console.size.width - 4, 20)
            max_rows = max(console.size.height - (4 if header else 3), 4)
            renderable = Markdown(tail_view(visible, width, max_rows))
            if header:
                renderable = Group(Text.from_markup(header), renderable)
            live.update(renderable)
    finally:
        if live is not None:
            live.stop()
            prompt_area.show()
    return raw
