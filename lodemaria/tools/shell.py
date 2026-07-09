"""Interactive shell sessions runnable from the chat, portable across OSes.

Each session wraps a subprocess started through the system shell (cmd.exe on
Windows, /bin/sh on POSIX, selected automatically by ``shell=True``). Output is
streamed live into the chat as a bordered "box" — a coloured gutter marks which
session each line belongs to, so several sessions can run at once without their
output becoming indistinguishable. The user can send lines to a session's stdin
(line-based interactivity: REPLs and prompts work; full-screen curses apps do
not).

Sessions are either user-started (``!<command>`` in the prompt) or agent-started
(the ``shell`` tool, after the user approves it). When an agent-started session
finishes it is pushed onto ``ShellManager.completions`` so the chat loop can feed
its output back to the model.
"""

import os
import queue
import re
import signal
import subprocess
import threading
from typing import Callable

_IS_WINDOWS = os.name == "nt"

# Commands that only print text ("echo ..." / "clear && echo ..."), which small
# models emit when they try to answer the user through the shell.
_ECHO_ONLY_RE = re.compile(r"^(?:clear\s*&&\s*)?echo\b\s*(.*)$", re.DOTALL)


def echo_payload(command: str) -> str | None:
    """The text an ``echo``/``clear && echo`` command would print, unquoted.

    Returns None when the command is anything other than a bare echo, meaning
    it must actually run.
    """
    match = _ECHO_ONLY_RE.match(command.strip())
    if not match:
        return None
    payload = match.group(1).strip()
    if len(payload) >= 2 and payload[0] == payload[-1] and payload[0] in "\"'":
        payload = payload[1:-1]
    return payload

from lodemaria.terminal import console

# Gutter colour cycled per session id, so concurrent sessions stay legible.
_COLORS = ("cyan", "green", "magenta", "yellow", "blue", "red")

# Tail of a finished agent session's output fed back to the model (a runaway
# command must not flood the context window).
SHELL_OUTPUT_MAX_CHARS = 6000


class ShellSession:
    """One running command. Spawns immediately; output pumps on a daemon thread.

    ``origin`` is "user" (started with ``!``) or "agent" (started via the shell
    tool). ``on_finish`` is invoked from the pump thread once the process exits.
    """

    def __init__(
        self,
        sid: int,
        command: str,
        origin: str,
        on_finish: Callable[["ShellSession"], None],
    ) -> None:
        self.id = sid
        self.command = command
        self.origin = origin
        self._on_finish = on_finish
        self.color = _COLORS[(sid - 1) % len(_COLORS)]
        self.returncode: int | None = None
        self._lines: list[str] = []
        self._lock = threading.Lock()

        # Isolate the child in its own process group / session so terminate()
        # can take down the whole tree (the shell AND anything it spawned),
        # not just the top-level shell — otherwise its children keep the output
        # pipe open and the session never appears to finish.
        group_kwargs = (
            {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            if _IS_WINDOWS else {"start_new_session": True}
        )
        self.proc = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # line-buffered so output appears as it is produced
            encoding="utf-8",
            errors="replace",
            cwd=os.getcwd(),
            **group_kwargs,
        )
        console.print(
            f"[bold {self.color}]┌─ shell #{self.id}[/] "
            f"[dim]({origin})[/] [white]$ {command}[/]"
        )
        threading.Thread(target=self._pump, daemon=True).start()

    @property
    def running(self) -> bool:
        return self.returncode is None

    def _pump(self) -> None:
        """Stream stdout (with stderr merged in) into the chat until EOF."""
        try:
            assert self.proc.stdout is not None
            for line in self.proc.stdout:
                line = line.rstrip("\n")
                with self._lock:
                    self._lines.append(line)
                console.print(f"[{self.color}]│[/] {line}")
        finally:
            self.returncode = self.proc.wait()
            console.print(
                f"[bold {self.color}]└─ shell #{self.id} finalizada "
                f"(código {self.returncode})[/]"
            )
            self._on_finish(self)

    def send(self, text: str) -> bool:
        """Write one line to the process's stdin. False if it can't be sent."""
        if not self.running or self.proc.stdin is None:
            return False
        try:
            self.proc.stdin.write(text + "\n")
            self.proc.stdin.flush()
        except (OSError, ValueError):
            return False
        console.print(f"[{self.color}]│[/] [dim]> {text}[/]")
        return True

    def output(self) -> str:
        with self._lock:
            return "\n".join(self._lines)

    def terminate(self) -> None:
        """Kill the whole process tree (shell + its children), cross-platform."""
        if not self.running:
            return
        try:
            if _IS_WINDOWS:
                # taskkill /T ends the process and every descendant by PID.
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                    capture_output=True,
                )
            else:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
        except (OSError, subprocess.SubprocessError):
            try:
                self.proc.kill()  # best-effort fallback
            except OSError:
                pass


class ShellManager:
    """Owns the live sessions and the queue of finished agent-started ones."""

    def __init__(self) -> None:
        self._sessions: dict[int, ShellSession] = {}
        self._next_id = 1
        self._lock = threading.Lock()
        self.completions: queue.Queue[ShellSession] = queue.Queue()

    def start(self, command: str, origin: str) -> ShellSession:
        with self._lock:
            sid = self._next_id
            self._next_id += 1
        # Popen runs outside the lock (it can block); register once ready.
        session = ShellSession(sid, command, origin, self._on_finish)
        with self._lock:
            self._sessions[sid] = session
        return session

    def _on_finish(self, session: ShellSession) -> None:
        with self._lock:
            self._sessions.pop(session.id, None)
        if session.origin == "agent":
            self.completions.put(session)

    def get(self, sid: int) -> ShellSession | None:
        with self._lock:
            return self._sessions.get(sid)

    def active_ids(self) -> list[int]:
        with self._lock:
            return sorted(self._sessions)

    def terminate_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            session.terminate()
