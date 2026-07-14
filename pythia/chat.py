"""The interactive chat session: user input → (tools) → model → answer."""

import itertools
import os
import queue
import random
import re
import signal
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from pythia import config
from pythia.config import (
    CODE_BUILD_TIMEOUT_SECONDS,
    CODE_MEGABRAIN_MODEL,
    CODE_OLLAMA_OPTIONS,
    CODE_REINDEX_IDLE_SECONDS,
    DELPHIC_MAXIMS,
    MAX_TOOL_CALLS,
    MEGABRAIN_MODEL,
    OLLAMA_OPTIONS,
    THINKING_LABELS,
)
from pythia.llm import Message, ask, strip_think, trim_messages
from pythia.prompts import (
    CODE_SYSTEM_PROMPT_TEMPLATE,
    JSON_FIX_SYS,
    MEGABRAIN_REWRITE_SYS,
    SYSTEM_PROMPT_TEMPLATE,
)
from pythia.research import DEEP_RESEARCH_RE, extract_topic, run_deep_research
from pythia.streaming import stream_markdown
from pythia.terminal import INTERRUPT, InputReader, console, prompt_area
from pythia.tools import (
    display_images,
    execute_tool_call,
    format_image_results,
    format_news_results,
    format_search_results,
    image_search,
    news_search,
    parse_tool_calls,
    show_answer_diagrams,
    web_search,
    write_project_documentation,
)
from pythia.tools.code_mode import (
    CodeFileError,
    build_info_line,
    detect_build_commands,
    parse_block_edits,
    prepare_create,
    prepare_edit,
    project_rel,
    register_code_tools,
)
from pythia.tools.registry import available_tools
from pythia.tools.shell import SHELL_OUTPUT_MAX_CHARS, ShellManager, echo_payload

MEGABRAIN_RE = re.compile(r"mega\s*brain", re.IGNORECASE)
BRACKET_TERM_RE = re.compile(r"\[([^\]]+)\]")

# When the user's message is about THIS project, web_search calls are
# redirected to project_search (the docs index answers better than the web).
PROJECT_SCOPE_RE = re.compile(r"this\s+project|este\s+projeto", re.IGNORECASE)

# Substrings that mark a "the model backend is unreachable" error (the Ollama
# server is down), across locales (WinError text is localized).
_CONN_ERR_MARKERS = ("10061", "recus", "refus", "connect")

# An answer that contains this but produced no parseable tool call is a
# BROKEN tool call (malformed JSON or a tool that does not exist) — it gets
# a repair pass instead of being shown to the user as prose.
_BROKEN_TOOL_CALL_RE = re.compile(r'\{\s*"tool"\s*:\s*"')


def _is_connection_error(error: Exception) -> bool:
    return any(m in str(error).lower() for m in _CONN_ERR_MARKERS)


# Fenced code blocks whose language marks them as a shell command.
_SHELL_LANGS = {"sh", "bash", "shell", "zsh"}
_CODE_BLOCK_RE = re.compile(r"```([^\n`]*)\r?\n(.*?)```", re.DOTALL)


def _sole_shell_command(text: str) -> str | None:
    """The command inside the answer's single shell code block, or None when it
    doesn't contain exactly one such block."""
    commands = []
    for lang, body in _CODE_BLOCK_RE.findall(strip_think(text)):
        if lang.strip().lower() in _SHELL_LANGS and body.strip():
            commands.append(body.strip())
    return commands[0] if len(commands) == 1 else None


# ── Header widgets: server/RAM stats, git branch (best-effort helpers) ────────

def _ollama_stats() -> tuple[bool, int]:
    """(server reachable now, bytes of RAM/VRAM the loaded models occupy)."""
    try:
        import ollama

        models = getattr(ollama.ps(), "models", None) or []
    except Exception:
        return False, 0
    return True, sum(int(getattr(m, "size", 0) or 0) for m in models)


def _total_ram_bytes() -> int | None:
    """Physical RAM of this machine, or None when it can't be determined."""
    try:
        if os.name == "nt":
            import ctypes

            class _MemStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = _MemStatus(dwLength=ctypes.sizeof(_MemStatus))
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
            return None
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except Exception:
        return None


def _ram_gauge(used_bytes: int) -> str:
    """A small 5-block gauge of the RAM the loaded models take, e.g.
    "🧠 ▮▮▯▯▯ 4.2/16GB" — just the used figure when total RAM is unknown."""
    used_gb = used_bytes / 2**30
    total = _total_ram_bytes()
    if not total:
        return f"🧠 {used_gb:.1f}GB em uso"
    filled = round(5 * min(used_bytes / total, 1))
    bar = "▮" * filled + "▯" * (5 - filled)
    return f"🧠 {bar} {used_gb:.1f}/{total / 2**30:.0f}GB"


def _git_branch() -> str | None:
    """The current git branch of the cwd, or None outside a repo / no git."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        )
    except Exception:
        return None
    branch = out.stdout.strip()
    return branch if out.returncode == 0 and branch else None


def pre_search_brackets(user_input: str, max_results: int) -> tuple[str, str]:
    """For each [term] in user_input, run searches before involving the model.

    Image search triggers when the prompt contains "image". News search
    triggers when the prompt contains "news", "notícia", or "noticia".
    Returns (clean_prompt, search_context).
    """
    terms = BRACKET_TERM_RE.findall(user_input)
    if not terms:
        return user_input, ""

    clean_prompt = BRACKET_TERM_RE.sub(r"\1", user_input)
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

        if do_images:
            console.print(f"[bold yellow]🖼️   Buscando imagens:[/bold yellow] [cyan]{term}[/cyan]")
            img_results = image_search(term, max_results=max_results)
            console.print(f"[dim]Encontrei {len(img_results)} imagem(ns) para '{term}'[/dim]")
            display_images(img_results)
            sections.append(f"=== Imagens para '{term}' ===\n{format_image_results(img_results)}")

        if do_news:
            console.print(f"[bold yellow]📰  Buscando notícias:[/bold yellow] [cyan]{term}[/cyan]")
            news_results = news_search(term, max_results=max_results)
            console.print(f"[dim]Encontrei {len(news_results)} notícia(s) para '{term}'[/dim]")
            sections.append(f"=== Notícias para '{term}' ===\n{format_news_results(news_results)}")

    return clean_prompt, "\n\n".join(sections)


class ChatSession:
    """One interactive session: owns the message history and the input reader."""

    def __init__(
        self, model: str, max_results: int, ensure_server=None,
        code_mode: bool = False,
    ) -> None:
        self.model = model  # may be upgraded to Megabrain mid-session
        self.max_results = max_results
        self._megabrain = False  # shown as a chip in the header badges
        # Code Mode (--code): coding-agent system prompt, the file tools
        # (read/edit/create), and the documentation routine run at startup.
        self.code_mode = code_mode
        # Set by an approved file change; once the session sits idle long
        # enough, the docs/search index is refreshed and the flag cleared.
        self._docs_stale = False
        self._last_activity = time.monotonic()
        # Edits applied since the last user message, as (rel, before, after).
        # An edit_file call that repeats or exactly reverts one of these is
        # refused — the signature of a do/undo loop. Cleared on user input so
        # an explicit "revert that" request is never mistaken for a loop.
        self._applied_edits: list[tuple[str, str, str]] = []
        # Auto-build: the detected command, run synchronously after every
        # applied change; its result goes back in the same feedback message.
        self._build_command: str | None = None
        build_info = ""
        if code_mode:
            register_code_tools()
            commands = detect_build_commands()
            self._build_command = commands[0] if commands else None
            build_info = build_info_line(commands)
        # Called with no args to (re)start the Ollama server; returns True when
        # it is reachable. Lets the chat recover from a dropped backend itself.
        self._ensure_server = ensure_server
        self.labels = itertools.cycle(THINKING_LABELS)
        self.reader = InputReader(prompt_area)
        self.shells = ShellManager()
        self.focus = 0  # 0 = chat; otherwise the id of the focused shell session
        self._streaming = False  # True while a model call is in flight
        # Set once a user message mentions "this project"; from then on
        # web_search is redirected to project_search for the whole session.
        self._project_scope = False
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
        is_windows = os.name == "nt"
        template = CODE_SYSTEM_PROMPT_TEMPLATE if code_mode else SYSTEM_PROMPT_TEMPLATE
        self.messages: list[Message] = [
            {"role": "system", "content": template.format(
                now=now,
                os_name="Windows" if is_windows else "Linux/Unix",
                shell_name="cmd.exe" if is_windows else "/bin/sh",
                build_info=build_info,
            )}
        ]

    def run(self, initial_prompt: str = "") -> None:
        self._print_header()
        self.reader.start()
        self.reader.allow()

        # A prompt passed on the command line is processed as the first message.
        if initial_prompt:
            self.reader.lines.put(initial_prompt)

        # On Windows, Ctrl+C is a SIGINT to the main thread (it never reaches the
        # reader as a "\x03" char the way it does on POSIX with ISIG disabled).
        # Route it through _on_sigint so it works both mid-generation (abort) and
        # at the prompt (finish the focused shell, or quit when on the chat).
        previous_sigint = None
        try:
            previous_sigint = signal.signal(signal.SIGINT, self._on_sigint)
        except (ValueError, OSError):
            pass  # not the main thread / unsupported: fall back to default

        try:
            # Code Mode always starts from fresh documentation, so the very
            # first project_search already answers from the current source.
            if self.code_mode:
                self._write_docs("docs")
            self._loop()
        except KeyboardInterrupt:
            console.print("\n[dim]Até mais![/dim]")
        finally:
            if previous_sigint is not None:
                try:
                    signal.signal(signal.SIGINT, previous_sigint)
                except (ValueError, OSError):
                    pass
            self.shells.terminate_all()

    def _on_sigint(self, *_) -> None:
        """Ctrl+C handler. Mid-generation it raises to abort the in-flight model
        call (which unwinds to run() and quits, as it did before). At the prompt
        it hands INTERRUPT to the loop, which decides: finish the focused shell,
        or quit when on the chat."""
        if self._streaming:
            raise KeyboardInterrupt
        self.reader.lines.put(INTERRUPT)

    @contextmanager
    def _generating(self):
        """Mark a main-thread model operation so Ctrl+C aborts it instead of
        queuing an INTERRUPT nobody reads until it finishes."""
        self._streaming = True
        try:
            yield
        finally:
            self._streaming = False

    def _print_header(self) -> None:
        console.clear()
        maxim = random.choice(DELPHIC_MAXIMS)
        console.print(Panel(
            Text(f"🐍  {maxim}", style="cyan italic"),
            expand=False, border_style="cyan",
        ))
        self._print_badges()
        console.print(
            f"[dim]Digite[/dim] [yellow]quit[/yellow] [dim]ou[/dim] "
            f"[yellow]exit[/yellow] [dim]para sair[/dim]\n"
        )

    def _print_badges(self) -> None:
        """The status-chip line(s) under the header: model, Megabrain state,
        Ollama reachability and the RAM the loaded models occupy — plus, in
        Code Mode, the project chip (folder · git branch · build command).
        Re-printed when Megabrain upgrades the model."""
        reachable, used = _ollama_stats()
        chips = [
            f"[bold green]🔮 {self.model}[/bold green]",
            "[magenta]⚡ megabrain[/magenta]" if self._megabrain
            else "[dim]⚡ megabrain off[/dim]",
            "[green]🟢 ollama[/green]" if reachable else "[red]🔴 ollama[/red]",
            _ram_gauge(used),
        ]
        console.print("[dim] · [/dim]".join(chips))
        if self.code_mode:
            parts = [os.path.basename(os.getcwd()) or os.getcwd()]
            branch = _git_branch()
            if branch:
                parts.append(branch)
            if self._build_command:
                parts.append(f"$ {self._build_command}")
            console.print(f"[dim]📦 {' · '.join(parts)}[/dim]")

    def _loop(self) -> None:
        while True:
            # Keep the routing hint (and focus) in sync with the live sessions.
            self._update_status()

            # An agent-started shell that just finished is reported first, so
            # the model reacts to its output before the next user message.
            try:
                finished = self.shells.completions.get_nowait()
            except queue.Empty:
                finished = None
            if finished is not None:
                self._report_shell(finished)
                continue

            # Poll (rather than block) so shell events stay responsive while
            # the user is idle at the prompt.
            try:
                user_input = self.reader.lines.get(timeout=0.2)
            except queue.Empty:
                self._maybe_reindex()
                continue
            self._last_activity = time.monotonic()

            if user_input is None:  # EOF / Ctrl+D → always quit
                console.print("\n[dim]Até mais![/dim]")
                break
            # quit/exit and Ctrl+C finish the FOCUSED shell (app keeps running);
            # on the chat itself they quit the app. Checked before routing so a
            # focused shell can't swallow them as stdin.
            if user_input is INTERRUPT or (
                isinstance(user_input, str)
                and user_input.strip().lower() in {"quit", "exit"}
            ):
                if self.focus and self.shells.get(self.focus):
                    self._finish_focused_shell()
                    self._update_status()
                    self.reader.allow()
                    continue
                console.print("[dim]Até mais![/dim]")
                break
            stripped = user_input.strip()
            if not stripped:
                self.reader.allow()
                continue
            # "!cmd", "@id" and stdin-for-a-focused-shell never reach the model.
            if self._route_input(stripped):
                self.reader.allow()
                continue

            queued = self.reader.lines.qsize()
            if queued:
                s = "ns" if queued > 1 else ""
                console.print(f"[dim]({queued} mensagem{s} na fila)[/dim]")

            self._handle_message(user_input)

    def _route_input(self, text: str) -> bool:
        """Handle shell control input. Returns True when the line was consumed
        as a shell command/stdin (so it must NOT be sent to the model)."""
        # "!<command>" — start a new user shell session and focus it.
        if text.startswith("!"):
            command = text[1:].strip()
            if not command:
                console.print("[yellow]Uso: !<comando>[/yellow]")
            else:
                session = self.shells.start(command, origin="user")
                self.focus = session.id
                self._update_status()
            return True

        # "@id" / "@chat" — move the input focus.
        if text.startswith("@"):
            target = text[1:].strip().lower()
            if target in ("chat", "0", ""):
                self.focus = 0
                console.print("[dim]Foco: chat[/dim]")
            elif target.isdigit() and self.shells.get(int(target)):
                self.focus = int(target)
                console.print(f"[dim]Foco: shell #{target}[/dim]")
            else:
                console.print(f"[yellow]Sessão '{target}' não encontrada.[/yellow]")
            self._update_status()
            return True

        # Focused on a shell → the line is stdin for that process.
        if self.focus:
            session = self.shells.get(self.focus)
            if session and session.send(text):
                return True
            self.focus = 0
            self._update_status()
            console.print("[dim]Sessão encerrada; foco de volta ao chat.[/dim]")
            return True

        return False

    def _finish_focused_shell(self) -> None:
        """Terminate the focused shell and return focus to the chat, leaving the
        rest of the app running."""
        session = self.shells.get(self.focus)
        if session is not None:
            session.terminate()
            console.print(f"[dim]Encerrando shell #{self.focus}...[/dim]")
        self.focus = 0

    def _update_status(self) -> None:
        """Refresh the routing hint under the prompt from the live sessions."""
        if self.focus and self.shells.get(self.focus) is None:
            self.focus = 0  # focused session ended
        ids = self.shells.active_ids()
        if not ids:
            prompt_area.set_base_status("")
            return
        if self.focus:
            session = self.shells.get(self.focus)
            command = session.command if session else ""
            if len(command) > 40:
                command = command[:39] + "…"
            where = f"shell #{self.focus} ($ {command})"
        else:
            where = "chat"
        listing = ", ".join(f"#{i}" for i in ids)
        hint = (
            "quit/exit/^C encerra a shell"
            if self.focus
            else "@<id> foca · quit/exit sai"
        )
        prompt_area.set_base_status(
            f"\033[2;36m{len(ids)} shell(s) ativa(s): {listing}  ·  foco: {where}"
            f"  ·  {hint} · @chat · !<cmd> nova\033[0m"
        )

    def _report_shell(self, session) -> None:
        """Feed a finished agent-started session's output back to the model."""
        output = session.output() or "(sem saída)"
        if len(output) > SHELL_OUTPUT_MAX_CHARS:
            output = "…[início truncado]\n" + output[-SHELL_OUTPUT_MAX_CHARS:]
        self.messages.append({"role": "user", "content": (
            f"The shell command you started (shell #{session.id}: "
            f"`{session.command}`) has finished with exit code "
            f"{session.returncode}.\n\nOutput:\n{output}\n\n"
            "Now answer the user or make another tool call."
        )})
        self._agent_loop()
        self._update_status()

    def _handle_message(self, user_input: str) -> None:
        # A new user message resets loop detection: if the user themselves
        # asks to revert a change, the inverse edit is legitimate.
        self._applied_edits.clear()
        # Checked on the ORIGINAL message (before any rewriting), so the flag
        # survives Megabrain restructuring the prompt. Once set, it stays on
        # for the rest of the session.
        if PROJECT_SCOPE_RE.search(user_input):
            self._project_scope = True

        # "docs" alone triggers the documentation writer, no model involved.
        if user_input.strip().lower() == "docs":
            self._write_docs(user_input)
            return

        if MEGABRAIN_RE.search(user_input):
            user_input = self._activate_megabrain(user_input)
            if not user_input:
                self.reader.allow()
                return

        # Deep research trigger — multi-phase autonomous research pipeline
        if DEEP_RESEARCH_RE.search(user_input):
            request = extract_topic(user_input)
            if not request:
                console.print(
                    "[yellow]Sobre o que devo pesquisar? Inclua um tópico junto de "
                    "'pesquisa profunda'.[/yellow]\n"
                )
                self.reader.allow()
                return
            self.reader.allow()  # keep input active so the timer renders above it
            if self._ensure_server:
                self._ensure_server()  # best-effort before the long pipeline
            try:
                with self._generating():  # allow Ctrl+C to abort the pipeline
                    report = run_deep_research(request, self.model, self.max_results)
            except Exception as e:
                self._report_model_error(e)
                return
            self.messages.append({"role": "user", "content": user_input})
            self.messages.append({"role": "assistant", "content": report})
            self.reader.allow()
            return

        # Pre-search any [bracketed] terms before sending to the model
        clean_input, search_context = pre_search_brackets(user_input, self.max_results)
        if search_context:
            console.print()
            content = (
                f"Contexto de pesquisa prévia:\n\n{search_context}\n\n"
                f"Pergunta do usuário: {clean_input}"
            )
        else:
            content = user_input

        self.messages.append({"role": "user", "content": content})
        self._agent_loop()

    def _maybe_reindex(self) -> None:
        """Refresh the docs/search index once the Code Mode session sits idle
        after approved writes, so project_search keeps answering from the
        current source instead of the pre-change one."""
        if not (self.code_mode and self._docs_stale):
            return
        if self.shells.active_ids():  # a build/test may still change files
            return
        if time.monotonic() - self._last_activity < CODE_REINDEX_IDLE_SECONDS:
            return
        self._docs_stale = False  # also stops retry loops when it fails
        console.print(
            "\n[dim]♻  Sessão ociosa — atualizando a documentação e o índice "
            "de busca...[/dim]"
        )
        try:
            with self._generating():  # let Ctrl+C abort the refresh
                summary = write_project_documentation()
        except Exception as e:
            console.print(f"[red]Falha ao reindexar o projeto: {e}[/red]\n")
            return
        console.print("[dim]Índice atualizado.[/dim]\n")
        # Recorded for the model only — no reply is generated for it.
        self.messages.append({"role": "user", "content": (
            "(automatic notice) The project documentation and search index "
            "were refreshed after your recent changes:\n" + summary
        )})
        self.reader.allow()

    def _write_docs(self, user_input: str) -> None:
        """Run the documentation writer and record its summary in the history."""
        console.print("\n[bold yellow]📚  Documentando o projeto...[/bold yellow]")
        try:
            with self._generating():  # let Ctrl+C abort documentation generation
                summary = write_project_documentation()
        except Exception as e:
            console.print(f"[red]Falha ao documentar o projeto: {e}[/red]\n")
            self.reader.allow()
            return
        console.print("[dim]Documentação concluída.[/dim]\n")
        self.messages.append({"role": "user", "content": user_input})
        self.messages.append({"role": "assistant", "content": summary})
        self.reader.allow()

    def _activate_megabrain(self, user_input: str) -> str:
        """Switch to the Megabrain model and rewrite the prompt in a more
        structured form (Megabrain mentions removed) before the agent sees it.

        Returns the rewritten prompt, or "" when the message contained nothing
        beyond the Megabrain trigger itself.
        """
        # Code Mode's Megabrain is a bigger CODER model, not the general one.
        target = CODE_MEGABRAIN_MODEL if self.code_mode else MEGABRAIN_MODEL
        self.model = target
        self._megabrain = True
        console.print("[bold magenta]⚡ Megabrain ativado.[/bold magenta]")
        self._print_badges()  # the model chip changed — show the new state

        # Only used to detect an empty message and as a last-resort fallback;
        # the rewriter gets the ORIGINAL text so it can drop the whole
        # surrounding expression (e.g. "Com o mega brain ativo, ...") instead
        # of us leaving a broken sentence behind.
        stripped = MEGABRAIN_RE.sub("", user_input).strip(" \t,.;:!?-")
        if not stripped:
            self.messages.append({"role": "assistant", "content": "Megabrain ativado."})
            return ""

        try:
            with self._generating():
                rewritten = ask(
                    target, MEGABRAIN_REWRITE_SYS, user_input, "Estruturando o prompt"
                ) or stripped
        except Exception:
            rewritten = stripped  # backend hiccup: fall back to the raw prompt
        console.print(
            Panel(Markdown(rewritten), title="Prompt reestruturado", border_style="magenta")
        )
        return rewritten

    def _agent_loop(self) -> None:
        """Let the model call tools until it produces a final plain-text answer."""
        for _ in range(MAX_TOOL_CALLS):
            self.reader.allow()  # show "Digite:"; SafeConsole keeps it below output
            try:
                assistant_text = self._stream_assistant()
            except Exception as e:  # keep the session alive on any model error
                self._report_model_error(e)
                return
            self.messages.append({"role": "assistant", "content": assistant_text})

            tool_calls = parse_tool_calls(assistant_text) or []
            # Code Mode: file changes come as ```<path>:before/after/new```
            # fenced blocks (easier for weak models than JSON), turned here
            # into the same edit_file/create_file calls. block_errors carry
            # feedback for malformed block usage (an unpaired before/after).
            block_errors: list[str] = []
            if self.code_mode:
                block_calls, block_errors = parse_block_edits(assistant_text)
                tool_calls += block_calls
            if not tool_calls and not block_errors and _BROKEN_TOOL_CALL_RE.search(
                strip_think(assistant_text)
            ):
                tool_calls = self._repair_tool_calls(assistant_text) or []
            if not tool_calls and not block_errors:
                # Plain answer — done (streamed live above; print the permanent render)
                console.print("[bold green]Pyth.IA:[/bold green]")
                console.print(Markdown(strip_think(assistant_text)))
                console.print()
                # An answer that mentions .puml files or writes PlantUML inline
                # gets the diagrams rendered as ASCII art right below it
                # (silently skipped when not possible).
                show_answer_diagrams(strip_think(assistant_text))
                # Proactive: if the answer proposes exactly one shell command,
                # offer to run it — as if the agent had requested the shell tool.
                command = _sole_shell_command(assistant_text)
                if command is None:
                    return
                feedback = self._run_agent_shell({"command": command})
                self.messages.append({"role": "user", "content": feedback})
                continue

            # Run every tool call the model batched into this turn, one at a
            # time and in the order the model emitted them, then report all
            # of their results back together in a single message. Any
            # malformed-block feedback is reported alongside them.
            feedbacks = list(block_errors)
            for i, tool_call in enumerate(tool_calls, 1):
                # Questions about "this project" are answered by the local docs
                # index, not the web: redirect web_search → project_search.
                if self._project_scope and tool_call.get("tool") == "web_search":
                    tool_call = {**tool_call, "tool": "project_search"}
                # The shell tool needs user approval and the session manager, both
                # of which live here — so it is handled in the chat layer instead of
                # the stateless tool registry ("shell" is Code Mode's name for the
                # same tool). Code Mode's file changes need the same approval flow.
                if tool_call.get("tool") in ("shell_of_last_resort", "shell"):
                    feedback = self._run_agent_shell(tool_call)
                elif tool_call.get("tool") in ("edit_file", "create_file"):
                    feedback = self._run_file_change(tool_call)
                else:
                    feedback = execute_tool_call(tool_call, self.max_results)
                    # A fresh read supersedes older copies of the same file in
                    # the history — collapse them before appending this one.
                    if (
                        self.code_mode
                        and tool_call.get("tool") == "read_file"
                        and feedback.startswith("Current content of")
                    ):
                        rel = project_rel(str(tool_call.get("path", "")))
                        if rel:
                            self._collapse_stale_reads(rel)
                if len(tool_calls) > 1:
                    feedback = f"=== Result {i}/{len(tool_calls)}: {tool_call.get('tool')} ===\n{feedback}"
                feedbacks.append(feedback)
            self.messages.append({"role": "user", "content": "\n\n".join(feedbacks)})

        console.print("[bold red]⚠️  Reached max tool-call iterations without a final answer.[/bold red]\n")

    def _repair_tool_calls(self, assistant_text: str) -> list[dict] | None:
        """The answer looked like a tool call but didn't parse — malformed
        JSON, or a tool that does not exist. Ask the default model, on a
        clean history listing every available tool (forged ones included),
        to rewrite it as a valid call. Returns the repaired call(s), or None
        when the repair itself failed (the answer then flows to the user as
        plain text, as before)."""
        console.print(
            "\n[dim]🩹  Chamada de ferramenta inválida — corrigindo o "
            "JSON...[/dim]"
        )
        try:
            with self._generating():
                reply = ask(
                    config.DEFAULT_MODEL,
                    JSON_FIX_SYS.format(tools="\n".join(available_tools())),
                    strip_think(assistant_text),
                    "Corrigindo JSON",
                )
        except Exception:
            return None
        calls = [
            call for call in parse_tool_calls(reply) or []
            # A call whose args are still "<placeholder>" is the repair model
            # echoing the templates, not a real correction — drop it.
            if not any(
                isinstance(v, str) and v.startswith("<") and v.endswith(">")
                for v in call.values()
            )
        ]
        if not calls:
            console.print(
                "[dim]Não foi possível corrigir a chamada; tratando como "
                "resposta comum.[/dim]\n"
            )
            return None
        return calls

    def _stream_assistant(self) -> str:
        """Stream one assistant turn, transparently (re)starting the Ollama
        server and retrying once if the backend connection drops."""
        def once() -> str:
            with self._generating():  # let Ctrl+C abort the in-flight generation
                return stream_markdown(
                    next(self.labels),
                    header="[bold green]Pyth.IA:[/bold green]",
                    suppress_json=True,
                    model=self.model,
                    messages=trim_messages(self.messages),
                    options=CODE_OLLAMA_OPTIONS if self.code_mode else OLLAMA_OPTIONS,
                )

        try:
            return once()
        except Exception as e:
            if self._ensure_server and _is_connection_error(e):
                console.print(
                    "[dim]Servidor do Ollama indisponível — reiniciando...[/dim]"
                )
                if self._ensure_server():
                    return once()  # recovered: retry the turn once
            raise

    def _report_model_error(self, error: Exception) -> None:
        """Show a friendly message when the model backend can't be reached,
        instead of letting the exception crash the whole session."""
        text = str(error) or error.__class__.__name__
        console.print("\n[bold red]⚠️  Não consegui falar com o modelo.[/bold red]")
        console.print(f"[red]{text}[/red]")
        if _is_connection_error(error):
            console.print(
                "[dim]Não consegui manter o servidor do Ollama no ar. Confirme "
                "que o 'ollama' está instalado e funcionando e tente de novo.[/dim]"
            )
        console.print()
        self.reader.allow()

    def _ask_line(self, prompt: str) -> str | None:
        """Print a prompt and read one line from the user (None on Ctrl+C/EOF)."""
        console.print(prompt)
        self.reader.allow()
        answer = self.reader.lines.get()
        self._last_activity = time.monotonic()
        return None if answer is INTERRUPT else answer

    # Answers accepted as approval, and the bare refusals that carry no
    # guidance. Anything else typed at an approval prompt is treated as a
    # refusal PLUS a message steering the agent's next step.
    _APPROVE_WORDS = {"y", "yes", "s", "sim"}
    _BARE_DENY_WORDS = {"", "n", "no", "não", "nao"}

    def _ask_approval(self, prompt: str) -> tuple[bool | None, str | None]:
        """Ask a yes/no approval question that also accepts free-form
        guidance. Returns (decision, guidance): decision is True (approved),
        False (refused) or None (aborted with Ctrl+C/EOF); guidance is the
        user's own message whenever they answered with something other than a
        bare yes/no, so the agent can be steered instead of just blocked."""
        answer = self._ask_line(prompt)
        if answer is None:
            return None, None
        text = answer.strip()
        if text.lower() in self._APPROVE_WORDS:
            return True, None
        guidance = None if text.lower() in self._BARE_DENY_WORDS else text
        return False, guidance

    def _run_agent_shell(self, call: dict) -> str:
        """Ask the user to approve an agent command and, if allowed, start it in
        the background. Returns the feedback string for the model."""
        command = str(call.get("command", "")).strip()
        if not command:
            return "The shell call had an empty 'command'. Provide the command to run."

        # A bare echo is the model trying to talk through the shell — there is
        # nothing to execute. Skip the approval prompt (and the terminal clear)
        # and hand the text straight back as if the command had run.
        echoed = echo_payload(command)
        if echoed is not None:
            console.print("[dim]🪄  echo interceptado — nada foi executado[/dim]\n")
            return (
                f"The user accepted the command: {command}\n"
                f"It ran and printed:\n{echoed}\n\n"
                "Now answer or make another tool call."
            )

        console.print(Panel(
            f"[bold white]$ {command}[/]",
            title="[bold yellow]Pyth.IA quer executar um comando[/]",
            border_style="yellow",
            expand=False,
        ))
        decision, guidance = self._ask_approval(
            "[bold yellow]Permitir? [s/N ou digite uma orientação][/bold yellow]"
        )
        if decision is None:
            return "The user aborted before approving the command; it was not run."
        if not decision:
            console.print("[red]Comando negado.[/red]\n")
            if guidance:
                return (
                    f"The user did NOT approve running: {command}\n"
                    f'Instead they told you: "{guidance}"\n'
                    "Follow their guidance for your next step."
                )
            return (
                f"The user DENIED permission to run: {command}\n"
                "Do not attempt to run it again. Continue without it or ask the "
                "user how to proceed."
            )

        session = self.shells.start(command, origin="agent")
        self._update_status()
        return (
            f"Approved. Started shell #{session.id} running: {command}\n"
            "It runs in the background and its full output will be delivered to "
            "you when it finishes. For now, briefly tell the user it is running "
            "(or make another tool call) — do not invent its output."
        )

    def _collapse_stale_reads(self, rel: str) -> None:
        """Replace older read_file results for `rel` in the history with a
        short stub. Their content is stale (the file changed, or a newer read
        exists) and a single blob of tens of thousands of chars can evict the
        user's actual request from the trimmed context — a classic cause of
        the model forgetting WHY it was editing."""
        marker = f"Current content of {rel}:"
        pattern = re.compile(
            re.escape(marker) + r".*?Now answer or make another tool call\.",
            re.DOTALL,
        )
        stub = (
            f"[stale content of {rel} — the file was changed or re-read "
            "since; call read_file again if needed]"
        )
        for msg in self.messages:
            if msg["role"] == "user" and marker in msg["content"]:
                msg["content"] = pattern.sub(stub, msg["content"])

    def _edit_loop_feedback(self, plan) -> str | None:
        """The refusal message for an edit_file call that repeats or exactly
        reverts an edit already applied since the last user message — the
        signature of a do/undo loop — or None when the edit is fine."""
        entry = (plan.rel, plan.before, plan.after)
        if (plan.rel, plan.after, plan.before) in self._applied_edits:
            return (
                f"edit_file refused: this change exactly REVERTS a change "
                f"you already applied to {plan.rel} — you are in a do/undo "
                "loop. Stop editing. Call read_file to see the file's "
                "current state, then tell the user what state it is in and "
                "why you are stuck."
            )
        if entry in self._applied_edits:
            return (
                f"edit_file refused: you already applied this exact change "
                f"to {plan.rel}. Do not repeat it — call read_file to "
                "confirm the current content, then continue with the next "
                "step or answer the user."
            )
        return None

    def _run_file_change(self, call: dict) -> str:
        """Show what an edit_file/create_file call would change — the exact
        snippet before/after, or the whole content for a new file — and, if
        the user approves, apply it. Returns the feedback for the model."""
        tool = call.get("tool")
        try:
            if tool == "create_file":
                plan = prepare_create(call.get("path", ""), call.get("content", ""))
            else:
                plan = prepare_edit(
                    call.get("path", ""), call.get("before", ""), call.get("after", "")
                )
        except CodeFileError as e:
            console.print(f"\n[red]{tool} recusado: {e}[/red]\n")
            return f"{tool} failed: {e}\n\nFix the call and try again."

        if not plan.is_new:
            loop_feedback = self._edit_loop_feedback(plan)
            if loop_feedback:
                console.print(
                    f"\n[red]{tool} recusado: loop de edição detectado em "
                    f"{plan.rel}[/red]\n"
                )
                return loop_feedback

        def code(snippet: str):
            if not snippet.strip():
                return Text("(vazio)", style="dim")
            return Syntax(
                snippet, Syntax.guess_lexer(plan.rel, snippet), word_wrap=True
            )

        if plan.is_new:
            title = f"[bold yellow]Pyth.IA quer criar o arquivo {plan.rel}[/]"
            body = code(plan.new_text)
        else:
            title = f"[bold yellow]Pyth.IA quer alterar o arquivo {plan.rel}[/]"
            body = Group(
                Text("── Antes ──", style="bold red"),
                code(plan.before),
                Text("── Depois ──", style="bold green"),
                code(plan.after),
            )
        console.print(Panel(body, title=title, border_style="yellow"))
        decision, guidance = self._ask_approval(
            "[bold yellow]Aplicar esta mudança? [s/N ou digite uma orientação]"
            "[/bold yellow]"
        )
        if decision is None:
            return (
                f"The user aborted before approving the change to {plan.rel}; "
                "nothing was written."
            )
        if not decision:
            console.print("[red]Mudança negada.[/red]\n")
            if guidance:
                # Explicit steering is fresh user intent — reset loop detection
                # so a change they asked for (e.g. a revert) is not blocked.
                self._applied_edits.clear()
                return (
                    f"The user did NOT approve the change to {plan.rel}; "
                    f'nothing was written. Instead they told you: "{guidance}"\n'
                    "Follow their guidance for your next step."
                )
            return (
                f"The user DENIED the change to {plan.rel}; nothing was "
                "written. Do not try the same change again — ask the user how "
                "to proceed instead."
            )

        try:
            plan.apply()
        except OSError as e:
            console.print(f"[red]Falha ao escrever {plan.rel}: {e}[/red]\n")
            return f"Writing {plan.rel} failed: {e}"
        self._docs_stale = True  # refresh the search index when idle
        console.print(f"[green]✔  {plan.rel} salvo.[/green]\n")
        if not plan.is_new:
            self._applied_edits.append((plan.rel, plan.before, plan.after))
            del self._applied_edits[:-20]
        # Any older read_file result for this file no longer matches the disk.
        self._collapse_stale_reads(plan.rel)
        applied = (
            f"{plan.rel} was created" if plan.is_new
            else f"the snippet in {plan.rel} was replaced"
        )
        feedback = f"Approved and applied: {applied}." + self._run_auto_build()
        excerpt = plan.applied_context()
        if excerpt is not None:
            feedback += (
                f"\n\nThe file now reads around your change:\n{excerpt}\n\n"
                "Before confirming to the user, verify the requested change "
                "is COMPLETE: every symbol you added (imports, variables, "
                "functions) must actually be USED. If anything is missing, "
                "make the next edit_file call now instead of confirming."
            )
        return feedback

    def _run_auto_build(self) -> str:
        """Build the project right after an applied change (the command was
        detected from the project itself, so no approval is asked) and WAIT
        for it, so the model gets the result in the same feedback message.
        Returns the whole feedback tail: the build output is only included
        when the build exits nonzero (words like "error" in the output are
        NOT trusted — "0 errors" and error-handling test names would read as
        failures and send the model chasing non-problems); a clean build is
        reported as just a success sentence."""
        if not self._build_command:
            return " Now briefly confirm to the user what changed."
        console.print(f"[dim]🔨  Build automático: $ {self._build_command}[/dim]")
        # origin="auto": streamed live like any session, but never queued for
        # _report_shell — the result is delivered synchronously right here.
        session = self.shells.start(self._build_command, origin="auto")
        start = time.monotonic()
        timed_out = False
        with self._generating():  # Ctrl+C aborts the wait (and the session)
            while session.running:
                if time.monotonic() - start > CODE_BUILD_TIMEOUT_SECONDS:
                    timed_out = True
                    session.terminate()
                time.sleep(0.1)
        self._update_status()
        if timed_out:
            return (
                f" The automatic build (`{self._build_command}`) was "
                f"terminated after {CODE_BUILD_TIMEOUT_SECONDS}s without "
                "finishing. Briefly confirm to the user what changed and "
                "mention the build seems stuck."
            )
        output = session.output()
        if session.returncode == 0:
            return (
                " The project was rebuilt automatically: build successful. "
                "Now briefly confirm to the user what changed."
            )
        if len(output) > SHELL_OUTPUT_MAX_CHARS:
            output = "…[início truncado]\n" + output[-SHELL_OUTPUT_MAX_CHARS:]
        return (
            f"\n\nThe automatic build (`{self._build_command}`) finished "
            f"with exit code {session.returncode} and reported problems:\n"
            f"{output or '(sem saída)'}\n\n"
            "If your change caused this, explain the problem to the user and "
            "propose a fix; otherwise briefly confirm what changed."
        )
