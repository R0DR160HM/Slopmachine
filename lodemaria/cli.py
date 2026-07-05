"""Command-line entry point: argument parsing and Ollama server lifecycle.

This module deliberately imports nothing from third-party packages at module
level, so a missing dependency produces a friendly message instead of a
traceback.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from importlib.util import find_spec

from lodemaria.config import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_MODEL,
    FORGE_MODEL,
    MEGABRAIN_MODEL,
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
        "prompt",
        nargs="*",
        help="Optional first prompt to send immediately "
             "(e.g. python -m lodemaria Qual é o seu nome?)",
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


def _start_ollama_server() -> subprocess.Popen:
    if shutil.which("ollama") is None:
        _install_ollama()
    try:
        proc = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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


def _installed_models() -> set[str]:
    """Return the tags already pulled, waiting for the server if needed."""
    import ollama

    for attempt in range(SERVER_LIST_RETRIES):
        try:
            listing = ollama.list()
        except Exception:
            time.sleep(0.5)
            continue
        return {
            _canonical(name)
            for m in getattr(listing, "models", None) or []
            if (name := getattr(m, "model", None) or getattr(m, "name", None))
        }
    sys.exit("❌  O servidor do Ollama não respondeu — tente novamente.")


def _canonical(name: str) -> str:
    """Ollama treats a tagless name as ':latest'; compare accordingly."""
    return name if ":" in name else f"{name}:latest"


def _ensure_models(chat_model: str) -> None:
    """Pull any model the app needs (chat, megabrain, forge) that is missing.

    `ollama pull` runs attached to the terminal so its own progress bar is
    visible during the download.
    """
    installed = _installed_models()
    needed = dict.fromkeys((chat_model, MEGABRAIN_MODEL, FORGE_MODEL))
    for model in needed:
        if _canonical(model) in installed:
            continue
        print(f"⬇️  Modelo '{model}' não encontrado localmente — baixando...")
        result = subprocess.run(["ollama", "pull", model])
        if result.returncode != 0:
            sys.exit(f"❌  Falha ao baixar o modelo '{model}'.")


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


def _stop(proc: subprocess.Popen) -> None:
    _unload_models()
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> None:
    _force_utf8_output()
    args = _parse_args()
    _check_dependencies()

    # Imported only after the dependency check — these pull in rich/ollama.
    from lodemaria.chat import ChatSession
    from lodemaria.terminal import raw_input_mode

    ollama_proc = _start_ollama_server()
    try:
        _ensure_models(args.model)
        with raw_input_mode():
            session = ChatSession(model=args.model, max_results=args.results)
            session.run(initial_prompt=" ".join(args.prompt).strip())
    finally:
        _stop(ollama_proc)
