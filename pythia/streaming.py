"""Live token-by-token rendering of model responses.

The response streams into a transient rich Live region rendered as Markdown,
so the user watches the answer being written. When the response completes the
region is erased and the caller prints the definitive rendering — or nothing,
when the response turns out to be a tool call.

While the live region is on screen the REAL bottom input prompt is hidden (the
two would fight over the same rows) — but the region re-draws the prompt and
the "Pensando... (Xs)" status line as its own last rows (_LiveView), refreshed
8x/s, so the timer keeps ticking and typed characters keep echoing throughout
the stream.
"""

import math

from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
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


def thinking_panel(notes: str, width: int, max_rows: int) -> Panel:
    """The reasoning notes as a dim panel, cropped to their tail — visibly
    NOT the final answer."""
    return Panel(
        Text(tail_view(notes, width, max_rows), style="dim italic"),
        title="[dim]💭 Raciocínio — não é a resposta final[/dim]",
        title_align="left",
        border_style="dim",
        expand=False,
    )


class _LiveView:
    """The Live region's renderable, rebuilt on every auto-refresh (8x/s).

    The streaming loops only mutate `thinking`/`answer`; rendering is pulled
    by rich's refresh thread through __rich__. That keeps the region alive
    between tokens: the real prompt area is hidden while the region is on
    screen, so its status line (the "Pensando... (Xs)" timer, which
    stream_chat updates every second) and the "Digite:" prompt with the
    typed buffer are re-drawn here as the region's last rows instead.
    """

    def __init__(
        self, header: str | None = None, thinking: str | None = None
    ) -> None:
        self.header = header
        self.thinking = thinking  # reasoning notes (grow during the pass)
        self.answer = ""  # streamed answer markdown (answer pass only)

    def __rich__(self) -> Group:
        width = max(console.size.width - 4, 20)
        height = console.size.height
        parts: list = []
        think_rows = 0
        if self.thinking:
            # The notes get most of the screen while they are alone, and a
            # third of it once the answer streams below them (the panel's
            # borders take 2 extra rows; the bottom prompt block, 2 more).
            think_rows = (
                max(height // 3, 4) if self.answer else max(height - 6, 4)
            )
            parts.append(thinking_panel(self.thinking, width, think_rows))
        if self.answer:
            if self.header:
                parts.append(Text.from_markup(self.header))
            # Keep the newest content on screen: crop to a tail that fits the
            # terminal (with margin for the header, the thinking panel, the
            # prompt block and markdown block spacing).
            max_rows = max(
                height
                - (4 if self.header else 3)
                - (think_rows + 2 if self.thinking else 0)
                - 2,
                4,
            )
            parts.append(Markdown(tail_view(self.answer, width, max_rows)))
        status, prompt = prompt_area.live_tail()
        if status:
            parts.append(Text.from_ansi(status))
        if prompt is not None:
            parts.append(Text.from_ansi(prompt))
        return Group(*parts)


def _start_live(view: _LiveView) -> Live:
    """Hide the real prompt (the view re-draws it inside the region) and
    start the transient Live around `view`."""
    prompt_area.hide()
    live = Live(
        view,
        console=console,
        transient=True,
        refresh_per_second=8,
        vertical_overflow="ellipsis",
    )
    live.start()
    return live


# While the reasoning pass's accumulated text may still turn out to be just
# "SKIP", nothing is rendered — a one-word panel flashing on screen is noise.
_SKIP_PREFIXES = {"S", "SK", "SKI", "SKIP"}


def stream_thinking(label: str, **chat_kwargs) -> str:
    """Stream one reasoning pass live, inside the dim "não é a resposta final"
    panel; return the raw full text.

    The region is transient: the notes stay on screen only while they stream.
    The answer pass then re-displays them (stream_markdown's `thinking`) for
    the rest of the turn, so the thought process is only truly erased when
    the final answer replaces it.
    """
    raw = ""
    view = _LiveView()
    live = None
    try:
        for raw in stream_chat(label, **chat_kwargs):
            visible = visible_text(raw).strip()
            if not visible or visible.upper() in _SKIP_PREFIXES:
                continue
            if live is None:
                live = _start_live(view)
            view.thinking = visible
    finally:
        if live is not None:
            live.stop()
            prompt_area.show()
    return raw


def stream_markdown(
    label: str,
    *,
    header: str | None = None,
    suppress_json: bool = False,
    thinking: str | None = None,
    **chat_kwargs,
) -> str:
    """Stream one chat response, rendering it live; return the raw full text.

    `header` (rich markup) is shown above the streaming text inside the
    transient region only — the caller prints the permanent version.

    With `suppress_json=True`, a response that opens with "{" or a code fence
    is kept off-screen (the "Pensando..." timer stays up instead): it is
    almost certainly a tool call, which is never displayed to the user.

    `thinking` (the reasoning pass's notes) is shown as a dim panel above the
    streaming answer for the whole turn — the region starts immediately so the
    notes never leave the screen while the model works — and is erased with
    the transient region when the turn ends: the permanent rendering printed
    by the caller never includes it.
    """
    raw = ""
    view = _LiveView(header=header, thinking=thinking)
    live = None
    try:
        if thinking:
            live = _start_live(view)
        for raw in stream_chat(label, **chat_kwargs):
            visible = visible_text(raw).strip()
            if not visible:
                continue
            if suppress_json and visible.startswith(("{", "```")):
                continue
            if live is None:
                live = _start_live(view)
            view.answer = visible
    finally:
        if live is not None:
            live.stop()
            prompt_area.show()
    return raw
