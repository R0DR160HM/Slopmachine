"""The interactive chat session: user input → (tools) → model → answer."""

import itertools
import re
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
from lodemaria.terminal import InputReader, console, prompt_area
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

MEGABRAIN_RE = re.compile(r"mega\s*brain", re.IGNORECASE)
BRACKET_TERM_RE = re.compile(r"\[([^\]]+)\]")


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

    def __init__(self, model: str, max_results: int) -> None:
        self.model = model  # may be upgraded to Megabrain mid-session
        self.max_results = max_results
        self.labels = itertools.cycle(THINKING_LABELS)
        self.reader = InputReader(prompt_area)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
        self.messages: list[Message] = [
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(now=now)}
        ]

    def run(self, initial_prompt: str = "") -> None:
        self._print_header()
        self.reader.start()
        self.reader.allow()

        # A prompt passed on the command line is processed as the first message.
        if initial_prompt:
            self.reader.lines.put(initial_prompt)

        try:
            self._loop()
        except KeyboardInterrupt:
            console.print("\n[dim]Até mais![/dim]")

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
            user_input = self.reader.lines.get()

            if user_input is None:
                console.print("\n[dim]Até mais![/dim]")
                break
            if not user_input:
                self.reader.allow()
                continue
            if user_input.lower() in {"quit", "exit"}:
                console.print("[dim]Até mais![/dim]")
                break

            queued = self.reader.lines.qsize()
            if queued:
                s = "ns" if queued > 1 else ""
                console.print(f"[dim]({queued} mensagem{s} na fila)[/dim]")

            self._handle_message(user_input)

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
            report = run_deep_research(request, self.model, self.max_results)
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

        rewritten = ask(
            MEGABRAIN_MODEL, MEGABRAIN_REWRITE_SYS, user_input, "Estruturando o prompt"
        ) or stripped
        console.print(
            Panel(Markdown(rewritten), title="Prompt reestruturado", border_style="magenta")
        )
        return rewritten

    def _agent_loop(self) -> None:
        """Let the model call tools until it produces a final plain-text answer."""
        for _ in range(MAX_TOOL_CALLS):
            self.reader.allow()  # show "Digite:"; SafeConsole keeps it below output
            assistant_text = stream_markdown(
                next(self.labels),
                header="[bold green]Lodemar.ia:[/bold green]",
                suppress_json=True,
                model=self.model,
                messages=trim_messages(self.messages),
                options=OLLAMA_OPTIONS,
            )
            self.messages.append({"role": "assistant", "content": assistant_text})

            tool_call = parse_tool_call(assistant_text)
            if tool_call is None:
                # Plain answer — done (streamed live above; print the permanent render)
                console.print("[bold green]Lodemar.ia:[/bold green]")
                console.print(Markdown(strip_think(assistant_text)))
                console.print()
                return

            feedback = execute_tool_call(tool_call, self.max_results)
            self.messages.append({"role": "user", "content": feedback})

        console.print("[bold red]⚠️  Reached max tool-call iterations without a final answer.[/bold red]\n")
