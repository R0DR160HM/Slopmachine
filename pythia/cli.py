"""Command-line entry point: argument parsing and Ollama server lifecycle.

This module deliberately imports nothing from third-party packages at module
level, so a missing dependency produces a friendly message instead of a
traceback.
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from importlib.util import find_spec

from pythia import config
from pythia.config import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_MODEL,
    SLOP_MODEL,
)

REQUIRED_PACKAGES = ("ollama", "ddgs", "rich")
SERVER_STARTUP_SECONDS = 1
SERVER_LIST_RETRIES = 10  # polls (0.5s apart) while waiting for the server

def _ollama_install_command() -> list[str]:
    """Official install command for the current OS (PowerShell on Windows, else sh)."""
    if os.name == "nt":
        return ["powershell", "-Command", "irm https://ollama.com/install.ps1 | iex"]
    return ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"]


def _install_ollama() -> None:
    """Install Ollama automatically using the official installer for this OS.

    Runs the installer attached to the terminal so its progress is visible.
    Exits with a friendly message if the installer tooling (curl/PowerShell)
    is itself missing or the installation fails.
    """
    print("⬇️  Ollama não encontrado — instalando automaticamente...")
    try:
        result = subprocess.run(_ollama_install_command())
    except FileNotFoundError:
        sys.exit(
            "❌  Não foi possível instalar o Ollama automaticamente "
            "(curl/PowerShell indisponível).\n"
            "    Instale manualmente em https://ollama.com/download e rode novamente."
        )
    if result.returncode != 0:
        sys.exit("❌  Falha ao instalar o Ollama automaticamente.")


def _parse_args() -> argparse.Namespace:
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
    parser.add_argument(
        "--slop",
        action="store_true",
        help=f"Use the tiniest model ({SLOP_MODEL}) for everything: chat, "
             "tool forging and per-file docs (overrides --model)",
    )
    parser.add_argument(
        "--code",
        action="store_true",
        help="Code Mode: a coding agent over the project in the current "
             "directory. Documents/indexes the project on startup and chats "
             "with the forge model by default (combines with --slop)",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional first prompt to send immediately "
             "(e.g. python -m pythia Qual é o seu nome?)",
    )
    return parser.parse_args()


def _force_utf8_output() -> None:
    """Make emoji-heavy output independent of the console code page.

    On Windows, redirected streams default to the ANSI code page (cp1252),
    which cannot encode the emoji used in the UI and crashes at startup; the
    same applies to non-UTF-8 locales on Linux.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _check_dependencies() -> None:
    missing = [pkg for pkg in REQUIRED_PACKAGES if find_spec(pkg) is None]
    if missing:
        sys.exit(f"❌  Missing dependencies: pip install {' '.join(missing)}")


def _detached_kwargs() -> dict:
    """Popen flags that detach a child from our console's Ctrl+C group.

    Windows delivers CTRL_C_EVENT to EVERY process sharing the console, so a
    Ctrl+C in the chat (e.g. to close a shell session) would otherwise also kill
    the Ollama server we launched. A new process group / session isolates it.
    """
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _start_ollama_server() -> subprocess.Popen:
    if shutil.which("ollama") is None:
        _install_ollama()
    try:
        proc = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **_detached_kwargs(),
        )
    except FileNotFoundError:
        # Just installed, but the new binary is not yet on this process's PATH
        # (common on Windows, where PATH changes need a fresh terminal).
        sys.exit(
            "❌  Ollama foi instalado, mas ainda não está disponível nesta sessão.\n"
            "    Reinicie o terminal e rode novamente."
        )
    time.sleep(SERVER_STARTUP_SECONDS)  # give the server a moment to start
    return proc


def _server_reachable() -> bool:
    """True when the Ollama server answers on its port right now."""
    try:
        import ollama

        ollama.ps()
        return True
    except Exception:
        return False


def _wait_reachable(retries: int = SERVER_LIST_RETRIES) -> bool:
    for _ in range(retries):
        if _server_reachable():
            return True
        time.sleep(0.5)
    return False


def _unload_models() -> None:
    """Ask the Ollama server to unload every loaded model, freeing RAM/VRAM.

    Terminating our `ollama serve` child is not enough: when a server was
    already running before the app started, our child exits immediately (port
    in use) and the models would stay loaded in the surviving server.
    """
    try:
        import ollama

        for running in getattr(ollama.ps(), "models", None) or []:
            name = getattr(running, "model", None) or getattr(running, "name", None)
            if name:
                ollama.generate(model=name, keep_alive=0)
    except Exception:
        pass  # shutdown must never fail because the server is already gone


def _terminate_tree(proc: subprocess.Popen) -> None:
    """Kill the server process AND its children — the ollama runner subprocesses
    that actually hold the models in memory.

    Since the server now runs in its own process group/session (so a Ctrl+C in
    the chat can't kill it), the console no longer cascades a shutdown to those
    runners on exit; we must take the whole tree down ourselves or the models
    stay resident.
    """
    if proc.poll() is not None:
        return  # already gone (e.g. our child exited: a server was already up)
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (OSError, subprocess.SubprocessError):
        try:
            proc.kill()  # best-effort fallback (single process only)
        except OSError:
            pass


def _stop(proc: subprocess.Popen) -> None:
    _unload_models()  # graceful VRAM/RAM release via the API first
    _terminate_tree(proc)  # then make sure no runner child is left behind
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass


def main() -> None:
    _force_utf8_output()
    args = _parse_args()
    if args.slop:
        args.model = SLOP_MODEL
        # forge.py and documentation.py read these through the config module
        # at call time, so overriding the attributes here reaches every call.
        config.FORGE_MODEL = SLOP_MODEL
        config.DEFAULT_MODEL = SLOP_MODEL
    if args.code and (args.slop or args.model == DEFAULT_MODEL):
        # Code Mode chats with the forge (coder) model unless the user picked
        # a model explicitly; under --slop that is the tiny coder tier.
        args.model = config.FORGE_MODEL
    _check_dependencies()

    # Imported only after the dependency check — these pull in rich/ollama.
    from pythia.chat import ChatSession
    from pythia.terminal import raw_input_mode

    state = {"proc": _start_ollama_server()}

    def ensure_server() -> bool:
        """(Re)start the Ollama server if it is not answering, so the user never
        has to launch it by hand. Returns True when the server is reachable."""
        if _server_reachable():
            return True
        old = state.get("proc")
        if old is not None:
            _terminate_tree(old)
        state["proc"] = _start_ollama_server()
        return _wait_reachable()

    try:
        # No model is pulled up front: each one is downloaded on first use,
        # when the Ollama server answers that it is not installed (llm.py).
        with raw_input_mode():
            session = ChatSession(
                model=args.model,
                max_results=args.results,
                ensure_server=ensure_server,
                code_mode=args.code,
            )
            session.run(initial_prompt=" ".join(args.prompt).strip())
    finally:
        _stop(state["proc"])
