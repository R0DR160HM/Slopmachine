"""Live token-by-token rendering of model responses.

The response streams into a transient rich Live region rendered as Markdown,
so the user watches the answer being written. When the response completes the
region is erased and the caller prints the definitive rendering — or nothing,
when the response turns out to be a tool call.

While the live region is on screen the bottom input prompt is hidden (the two
would fight over the same rows); keystrokes typed meanwhile keep accumulating
and reappear when the prompt is restored.
"""

from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

from lodemaria.llm import stream_chat, visible_text
from lodemaria.terminal import console, prompt_area


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
            renderable = Markdown(visible)
            if header:
                renderable = Group(Text.from_markup(header), renderable)
            live.update(renderable)
    finally:
        if live is not None:
            live.stop()
            prompt_area.show()
    return raw
