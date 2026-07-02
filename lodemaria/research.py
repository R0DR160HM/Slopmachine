"""Deep research mode: a multi-phase autonomous research pipeline.

Triggered when the user's message matches DEEP_RESEARCH_RE. The pipeline
interprets the request, gathers an overview, writes an abstract, derives
subtopics, dives into each one, synthesizes a report and closes with images.
"""

import re

from rich.markdown import Markdown
from rich.panel import Panel

from lodemaria import prompts
from lodemaria.config import DEEP_FETCH_TOP, DEEP_SUBTOPICS, OLLAMA_OPTIONS
from lodemaria.llm import ask, parse_list, strip_think
from lodemaria.streaming import stream_markdown
from lodemaria.terminal import console
from lodemaria.tools import (
    display_images,
    fetch_url,
    format_news_results,
    format_search_results,
    image_search,
    news_search,
    web_search,
)

DEEP_RESEARCH_RE = re.compile(r"deep\s*research|pesquisa\s+profunda", re.IGNORECASE)


def _ask_streamed(model: str, system: str, user: str, label: str) -> str:
    """One-shot model call rendered live as it streams; returns cleaned text.

    Used for the phases whose output the user reads (abstract, final report);
    internal phases use the non-displayed llm.ask instead.
    """
    raw = stream_markdown(
        label,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options=OLLAMA_OPTIONS,
    )
    return strip_think(raw)


def extract_topic(user_input: str) -> str:
    """Clean up the user's message (stray brackets etc.) to get the topic."""
    topic = user_input.replace("[", "").replace("]", "")
    return topic.strip(" :–—-,.\t\n")


def _focus_query(keywords: str, sub: str) -> str:
    """Force the main-object keywords into every search query.

    `keywords` is the specific object of the research (e.g. a game's name).
    Unless the query already contains that exact phrase, we prepend it — so
    searches never drift to generic pages like a wiki's global "Characters"
    list when the user actually wanted a specific game's characters.
    """
    keywords, sub = keywords.strip(), sub.strip()
    if not keywords:
        return sub
    if keywords.lower() in sub.lower():
        return sub
    return f"{keywords} {sub}"


def gather_research(query: str, max_results: int, do_news: bool = True) -> str:
    """Run text + news search for a query and fetch the top links; return context."""
    sections: list[str] = []

    console.print(f"  [bold yellow]🔍  Texto:[/bold yellow] [cyan]{query}[/cyan]")
    text_results = web_search(query, max_results=max_results)
    console.print(f"  [dim]{len(text_results)} resultado(s)[/dim]")
    sections.append(f"Resultados de texto:\n{format_search_results(text_results)}")

    if do_news:
        console.print(f"  [bold yellow]📰  Notícias:[/bold yellow] [cyan]{query}[/cyan]")
        news_results = news_search(query, max_results=max_results)
        console.print(f"  [dim]{len(news_results)} notícia(s)[/dim]")
        sections.append(f"Notícias:\n{format_news_results(news_results)}")

    # Fetch the full text of the most promising links (snippets are short).
    fetched = 0
    for r in text_results:
        if fetched >= DEEP_FETCH_TOP:
            break
        url = r.get("href", "")
        if not url:
            continue
        console.print(f"  [bold yellow]🌐  Lendo:[/bold yellow] [cyan]{url}[/cyan]")
        page = fetch_url(url)
        sections.append(f"Conteúdo de {url}:\n{page}")
        fetched += 1

    return "\n\n".join(sections)


def run_deep_research(request: str, model: str, max_results: int) -> str:
    """Multi-phase research: interpret → overview → abstract → subtopics → dives → report."""
    console.print(Panel(
        f"[bold]🔬 Pesquisa profunda[/bold]\n[dim]{request}[/dim]",
        border_style="magenta", expand=False,
    ))

    # Phase 1 — let the model decide what to search for, from the user's request
    console.print("\n[bold magenta]▸ Fase 1/7[/bold magenta] — interpretando o pedido")
    topic = ask(
        model, prompts.QUERY_SYS,
        f"Mensagem do usuário: {request}",
        "Interpretando",
    ).splitlines()[0].strip().strip('"').strip() or request
    console.print(f"[dim]Consulta de busca:[/dim] [cyan]{topic}[/cyan]")

    # Extract the 2-3 keywords that define the main object of the search. These
    # are forced into every subtopic and image query so the research never
    # drifts to generic pages (e.g. a wiki's global "Characters" list).
    kw_raw = ask(
        model, prompts.KEYWORDS_SYS,
        f"Mensagem do usuário: {request}",
        "Extraindo palavras-chave",
    )
    keywords = " ".join(parse_list(kw_raw, 3)).strip() or topic
    console.print(f"[dim]Palavras-chave centrais:[/dim] [bold cyan]{keywords}[/bold cyan]")

    # Phase 2 — general research on the topic
    console.print("\n[bold magenta]▸ Fase 2/7[/bold magenta] — pesquisa geral")
    overview = gather_research(topic, max_results, do_news=True)

    # Phase 3 — write an abstract from the overview
    console.print("\n[bold magenta]▸ Fase 3/7[/bold magenta] — redigindo resumo")
    console.print("[bold cyan]Resumo:[/bold cyan]")
    abstract = _ask_streamed(
        model, prompts.ABSTRACT_SYS,
        f"Tópico: {topic}\n\nMaterial de pesquisa:\n{overview}",
        "Resumindo",
    )
    console.print(Markdown(abstract))

    # Phase 4 — derive subtopics from the abstract
    console.print("\n[bold magenta]▸ Fase 4/7[/bold magenta] — definindo subtópicos")
    subtopics_raw = ask(
        model, prompts.SUBTOPICS_SYS,
        f"Tópico: {topic}\n\nPalavras-chave centrais (inclua em CADA subtópico): "
        f"{keywords}\n\nResumo:\n{abstract}",
        "Planejando",
    )
    subtopics = parse_list(subtopics_raw, DEEP_SUBTOPICS) or [topic]
    console.print("[dim]Subtópicos:[/dim] " + ", ".join(f"[cyan]{s}[/cyan]" for s in subtopics))

    # Phase 5 — deep research on each subtopic
    console.print("\n[bold magenta]▸ Fase 5/7[/bold magenta] — aprofundando cada subtópico")
    deep_sections: list[str] = []
    for i, sub in enumerate(subtopics, 1):
        query = _focus_query(keywords, sub)
        console.print(f"\n[bold]({i}/{len(subtopics)}) {query}[/bold]")
        ctx = gather_research(query, max_results, do_news=True)
        deep_sections.append(f"### {query}\n{ctx}")

    # Phase 6 — synthesize everything into one cohesive report
    console.print("\n[bold magenta]▸ Fase 6/7[/bold magenta] — sintetizando relatório")
    material = (
        f"TÓPICO: {topic}\n\n=== RESUMO GERAL ===\n{abstract}\n\n"
        f"=== APROFUNDAMENTO ===\n" + "\n\n".join(deep_sections)
    )
    console.print("[bold green]🔬 Pesquisa Profunda — Lodemar.ia:[/bold green]")
    report = _ask_streamed(
        model, prompts.SYNTH_SYS,
        f"Material completo de pesquisa:\n\n{material}",
        "Sintetizando",
    )
    console.print(Markdown(report))
    console.print()

    # Phase 7 — relevant images to close it off
    console.print("\n[bold magenta]▸ Fase 7/7[/bold magenta] — imagens relevantes")
    img_raw = ask(
        model, prompts.IMG_QUERIES_SYS,
        f"Tópico: {topic}\nSubtópicos: {', '.join(subtopics)}",
        "Escolhendo imagens",
    )
    for q in parse_list(img_raw, 3) or [topic]:
        q = _focus_query(keywords, q)
        console.print(f"[bold yellow]🖼️   Buscando imagens:[/bold yellow] [cyan]{q}[/cyan]")
        imgs = image_search(q, max_results=max_results)
        console.print(f"[dim]{len(imgs)} imagem(ns)[/dim]")
        display_images(imgs)

    console.print()
    return report
