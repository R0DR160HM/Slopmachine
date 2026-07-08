"""The interactive chat session: user input → (tools) → model → answer."""

import itertools
import os
import queue
import re
import signal
from datetime import datetime

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from lodemaria.config import (
    MAX_TOOL_CALLS,
    MEGABRAIN_MODEL,
    OLLAMA_OPTIONS,
    THINKING_LABELS,
)
from lodemaria.llm import Message, ask, strip_think, trim_messages
from lodemaria.prompts import MEGABRAIN_REWRITE_SYS, SYSTEM_PROMPT_TEMPLATE
from lodemaria.research import DEEP_RESEARCH_RE, extract_topic, run_deep_research
from lodemaria.streaming import stream_markdown
from lodemaria.terminal import INTERRUPT, InputReader, console, prompt_area
from lodemaria.tools import (
    display_images,
    execute_tool_call,
    format_image_results,
    format_news_results,
    format_search_results,
    image_search,
    news_search,
    parse_tool_call,
    web_search,
    write_project_documentation,
)
from lodemaria.tools.shell import SHELL_OUTPUT_MAX_CHARS, ShellManager

MEGABRAIN_RE = re.compile(r"mega\s*brain", re.IGNORECASE)
BRACKET_TERM_RE = re.compile(r"\[([^\]]+)\]")

# Substrings that mark a "the model backend is unreachable" error (the Ollama
# server is down), across locales (WinError text is localized).
_CONN_ERR_MARKERS = ("10061", "recus", "refus", "connect")


def _is_connection_error(error: Exception) -> bool:
    return any(m in str(error).lower() for m in _CONN_ERR_MARKERS)


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

    def __init__(self, model: str, max_results: int, ensure_server=None) -> None:
        self.model = model  # may be upgraded to Megabrain mid-session
        self.max_results = max_results
        # Called with no args to (re)start the Ollama server; returns True when
        # it is reachable. Lets the chat recover from a dropped backend itself.
        self._ensure_server = ensure_server
        self.labels = itertools.cycle(THINKING_LABELS)
        self.reader = InputReader(prompt_area)
        self.shells = ShellManager()
        self.focus = 0  # 0 = chat; otherwise the id of the focused shell session
        self._streaming = False  # True while a model call is in flight
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
        is_windows = os.name == "nt"
        self.messages: list[Message] = [
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(
                now=now,
                os_name="Windows" if is_windows else "Linux/Unix",
                shell_name="cmd.exe" if is_windows else "/bin/sh",
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

    def _print_header(self) -> None:
        console.clear()
        header = Text("🦙  Lodemar.IA Chat", style="bold cyan")
        console.print(Panel(header, expand=False, border_style="cyan"))
        console.print(
            f"[dim]Modelo:[/dim] [green]{self.model}[/green]  "
            f"[dim]|  Digite[/dim] [yellow]quit[/yellow] [dim]ou[/dim] "
            f"[yellow]exit[/yellow] [dim]para sair[/dim]\n"
        )

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
                continue

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
            self._streaming = True  # allow Ctrl+C to abort the pipeline
            try:
                report = run_deep_research(request, self.model, self.max_results)
            except Exception as e:
                self._report_model_error(e)
                return
            finally:
                self._streaming = False
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

    def _write_docs(self, user_input: str) -> None:
        """Run the documentation writer and record its summary in the history."""
        console.print("\n[bold yellow]📚  Documentando o projeto...[/bold yellow]")
        try:
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
        self.model = MEGABRAIN_MODEL
        console.print("[bold magenta]⚡ Megabrain ativado.[/bold magenta]")

        # Only used to detect an empty message and as a last-resort fallback;
        # the rewriter gets the ORIGINAL text so it can drop the whole
        # surrounding expression (e.g. "Com o mega brain ativo, ...") instead
        # of us leaving a broken sentence behind.
        stripped = MEGABRAIN_RE.sub("", user_input).strip(" \t,.;:!?-")
        if not stripped:
            self.messages.append({"role": "assistant", "content": "Megabrain ativado."})
            return ""

        try:
            rewritten = ask(
                MEGABRAIN_MODEL, MEGABRAIN_REWRITE_SYS, user_input, "Estruturando o prompt"
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

            tool_call = parse_tool_call(assistant_text)
            if tool_call is None:
                # Plain answer — done (streamed live above; print the permanent render)
                console.print("[bold green]Lodemar.ia:[/bold green]")
                console.print(Markdown(strip_think(assistant_text)))
                console.print()
                return

            # The shell tool needs user approval and the session manager, both
            # of which live here — so it is handled in the chat layer instead of
            # the stateless tool registry.
            if tool_call.get("tool") == "shell":
                feedback = self._run_agent_shell(tool_call)
            else:
                feedback = execute_tool_call(tool_call, self.max_results)
            self.messages.append({"role": "user", "content": feedback})

        console.print("[bold red]⚠️  Reached max tool-call iterations without a final answer.[/bold red]\n")

    def _stream_assistant(self) -> str:
        """Stream one assistant turn, transparently (re)starting the Ollama
        server and retrying once if the backend connection drops."""
        def once() -> str:
            self._streaming = True  # let Ctrl+C abort the in-flight generation
            try:
                return stream_markdown(
                    next(self.labels),
                    header="[bold green]Lodemar.ia:[/bold green]",
                    suppress_json=True,
                    model=self.model,
                    messages=trim_messages(self.messages),
                    options=OLLAMA_OPTIONS,
                )
            finally:
                self._streaming = False

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
        return None if answer is INTERRUPT else answer

    def _run_agent_shell(self, call: dict) -> str:
        """Ask the user to approve an agent command and, if allowed, start it in
        the background. Returns the feedback string for the model."""
        command = str(call.get("command", "")).strip()
        if not command:
            return "The shell call had an empty 'command'. Provide the command to run."

        console.print(Panel(
            f"[bold white]$ {command}[/]",
            title="[bold yellow]Lodemar.ia quer executar um comando[/]",
            border_style="yellow",
            expand=False,
        ))
        answer = self._ask_line("[bold yellow]Permitir? [y/N][/bold yellow]")
        if answer is None:
            return "The user aborted before approving the command; it was not run."
        if answer.strip().lower() not in ("y", "yes", "s", "sim"):
            console.print("[red]Comando negado.[/red]\n")
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
