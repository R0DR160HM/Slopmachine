"""Thread-safe terminal I/O, portable across Windows and POSIX.

Keeps a "Digite:" input prompt (plus an optional status line) pinned to the
bottom of the screen while other threads print above it. A single lock guards
both the input buffer and stdout writes so that concurrent prints erase the
prompt block, print their content, then redraw it in place.

Input is read character-by-character: via msvcrt on Windows, and via
termios/select (with echo, canonical mode and ISIG disabled, so Ctrl+C arrives
as a plain "\\x03" character on both platforms) on POSIX.
"""

import contextlib
import os
import queue
import sys
import threading
import time

from rich.console import Console

PROMPT = "\033[1;34mDigite: \033[0m"

QUIT_COMMANDS = frozenset({"quit", "exit"})

# Delivered on the input queue when the user presses Ctrl+C. Unlike None (EOF /
# Ctrl+D, which always quits), this lets the chat loop decide what to do based on
# what is focused — e.g. terminate the focused shell instead of the whole app.
INTERRUPT = object()

_IS_WINDOWS = os.name == "nt"

if _IS_WINDOWS:
    import msvcrt

    @contextlib.contextmanager
    def raw_input_mode():
        """No-op on Windows: msvcrt already reads unbuffered, unechoed keys."""
        yield

    def read_char(timeout: float = 0.01) -> str | None:
        """Return the next typed character, or None after `timeout` seconds."""
        if msvcrt.kbhit():
            return msvcrt.getwch()
        time.sleep(timeout)
        return None

else:
    import select
    import termios

    @contextlib.contextmanager
    def raw_input_mode():
        """Disable echo, canonical mode and ISIG for the duration of the app.

        ISIG is cleared so Ctrl+C is delivered as a "\\x03" character (same as
        on Windows) instead of raising SIGINT mid-redraw. Settings are always
        restored on exit.
        """
        if not sys.stdin.isatty():
            yield
            return
        fd = sys.stdin.fileno()
        saved = termios.tcgetattr(fd)
        raw = termios.tcgetattr(fd)
        raw[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG)
        termios.tcsetattr(fd, termios.TCSADRAIN, raw)
        try:
            yield
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)

    def read_char(timeout: float = 0.01) -> str | None:
        """Return the next typed character, or None after `timeout` seconds."""
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            return sys.stdin.read(1)
        return None


class PromptArea:
    """Owns the bottom-of-screen input area (status line + prompt).

    All public methods are self-locking; ``lock`` is re-entrant so callers
    (e.g. SafeConsole) can hold it across an erase → print → redraw sequence.
    """

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self._buffer: list[str] = []
        self._active = False  # the reader is collecting a line
        self._suspended = False  # the area is temporarily hidden (live streaming)
        self._status = ""  # transient status (e.g. the "Pensando..." timer)
        self._base_status = ""  # persistent status shown when no transient one is set
        self._nlines = 2

    @property
    def visible(self) -> bool:
        return self._active and not self._suspended

    def _block(self) -> tuple[str, int]:
        """Return (text, line_count) for the bottom input area.

        When a status line is set (e.g. the live "Pensando..." timer), it is
        drawn just above the prompt; otherwise the prompt keeps its usual
        single blank line above it. A transient status (the live timer) takes
        precedence over the persistent base status (the shell routing hint).
        """
        buffer = "".join(self._buffer)
        status = self._status or self._base_status
        if status:
            return f"\n{status}\n{PROMPT}{buffer}", 3
        return f"\n{PROMPT}{buffer}", 2

    def erase(self) -> None:
        """Erase the currently-drawn block (cursor ends where it started)."""
        sys.stdout.write("\r\033[2K")
        for _ in range(self._nlines - 1):
            sys.stdout.write("\033[1A\033[2K")

    def draw(self) -> None:
        """Draw the block and remember how many lines it occupies."""
        block, self._nlines = self._block()
        sys.stdout.write(block)
        sys.stdout.flush()

    def set_status(self, text: str) -> None:
        """Update the live (transient) status line above the prompt, redrawing
        in place. Clearing it (text="") reveals the base status again."""
        with self.lock:
            self._status = text
            if self.visible:
                self.erase()
                self.draw()

    def set_base_status(self, text: str) -> None:
        """Set the persistent status line shown whenever no transient status is
        active (used for the running-shell routing hint). No-op if unchanged."""
        with self.lock:
            if text == self._base_status:
                return
            self._base_status = text
            if self.visible and not self._status:
                self.erase()
                self.draw()

    def write(self, text: str) -> None:
        """Write raw text to stdout, keeping the prompt at the bottom."""
        with self.lock:
            if self.visible:
                self.erase()
            sys.stdout.write(text)
            sys.stdout.flush()
            if self.visible:
                self.draw()

    def live_tail(self) -> tuple[str | None, str | None]:
        """Snapshot of the bottom block — (status line, prompt line with the
        typed buffer), each None/"" when absent — for re-drawing INSIDE a rich
        Live region while the real prompt is hidden, so the "Pensando..."
        timer and the input line stay on screen during streaming.

        Deliberately lock-free: it is called from the Live refresh thread,
        and taking `lock` there could deadlock against a SafeConsole.print
        that holds `lock` while waiting on the console's internal lock.
        A slightly stale status/buffer is harmless for display.
        """
        status = self._status or self._base_status
        prompt = (PROMPT + "".join(self._buffer)) if self._active else None
        return status, prompt

    def hide(self) -> None:
        """Take the prompt off the screen (e.g. while a live region renders).

        Typed characters keep accumulating unechoed until show() redraws them
        — though a live region that embeds live_tail() echoes them meanwhile.
        """
        with self.lock:
            if self.visible:
                self.erase()
            self._suspended = True

    def show(self) -> None:
        """Restore the prompt hidden by hide(), including anything typed since."""
        with self.lock:
            self._suspended = False
            if self._active:
                self.draw()

    # ── Input-side operations (used by InputReader) ──────────────────────────

    def begin_input(self) -> None:
        with self.lock:
            self._buffer = []
            self._active = True
            if not self._suspended:
                self.draw()

    def type_char(self, ch: str) -> None:
        with self.lock:
            self._buffer.append(ch)
            if self.visible:
                sys.stdout.write(ch)
                sys.stdout.flush()

    def backspace(self) -> None:
        with self.lock:
            if self._buffer:
                self._buffer.pop()
                if self.visible:
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()

    def submit(self) -> str:
        """Close the input area and return the typed line (stripped)."""
        with self.lock:
            if self.visible:
                sys.stdout.write("\n")
                sys.stdout.flush()
            self._active = False
            line = "".join(self._buffer).strip()
            self._buffer = []
            return line

    def deactivate(self) -> None:
        with self.lock:
            self._active = False


class SafeConsole(Console):
    """Rich Console whose print() erases/restores the input prompt."""

    def __init__(self, area: PromptArea, **kwargs) -> None:
        super().__init__(**kwargs)
        self._area = area

    def print(self, *args, **kwargs) -> None:  # type: ignore[override]
        with self._area.lock:
            if self._area.visible:
                self._area.erase()
            super().print(*args, **kwargs)
            if self._area.visible:
                self._area.draw()


class InputReader:
    """Reads user input character-by-character on a background thread.

    Submitted lines are delivered through ``lines``. ``None`` signals EOF /
    Ctrl+D (the app should quit); ``INTERRUPT`` signals Ctrl+C (the chat loop
    decides what to do). The prompt is only shown after ``allow()`` — the chat
    loop calls it once it is ready for the next message. The thread keeps running
    across quit commands and interrupts; only a real EOF stops it, since the app
    lifecycle is now owned by the chat loop.
    """

    def __init__(self, area: PromptArea) -> None:
        self._area = area
        self._gate = threading.Event()
        self.lines: queue.Queue = queue.Queue()

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def allow(self) -> None:
        """Open the prompt for the next line of input."""
        self._gate.set()

    def _run(self) -> None:
        while True:
            self._gate.wait()
            self._gate.clear()
            self._area.begin_input()
            if not self._read_line():
                return

    def _read_line(self) -> bool:
        """Read one line; return False when the reader thread should stop.

        Only a real EOF (stdin closed) or Ctrl+D stops the reader. A submitted
        line — including a quit command — and Ctrl+C are delivered to the chat
        loop, which owns the decision to actually quit; the reader keeps running
        so the app can survive them (e.g. Ctrl+C on a focused shell).
        """
        while True:
            ch = read_char()
            if ch is None:
                continue
            if ch in ("", "\x04"):  # EOF / Ctrl+D: stdin closing → quit for good
                self._area.deactivate()
                self.lines.put(None)
                return False
            if ch in ("\r", "\n"):
                line = self._area.submit()
                self.lines.put(line)
                return True
            if ch == "\x03":  # Ctrl+C: let the chat loop decide (quit vs. shell)
                self._area.submit()
                self.lines.put(INTERRUPT)
                return True
            if ch in ("\x08", "\x7f"):  # backspace (Windows / POSIX)
                self._area.backspace()
            elif ch in ("\x00", "\xe0"):  # Windows special-key prefix: swallow
                read_char(0)
            elif ch == "\x1b":  # POSIX escape sequence (arrows etc.): swallow
                while read_char(0.005):
                    pass
            elif ord(ch) >= 32:
                self._area.type_char(ch)


# Shared singletons — one terminal, one prompt area, one console.
prompt_area = PromptArea()
console = SafeConsole(prompt_area)
