"""DuckDuckGo search (text, image, news) and result formatting."""

import re

from ddgs import DDGS

from pythia.config import DEFAULT_MAX_RESULTS

# Terms that mark an image result as inappropriate. The first group is
# matched as plain substrings (unambiguous even inside concatenated URL
# slugs like "freepornvideos"); the \b-bounded group avoids false positives
# on innocent words (sussex, canal, document, ...).
_NSFW_RE = re.compile(
    r"porn|pornhub|xvideos|xnxx|onlyfans|hentai|nsfw|milf|blowjob|handjob"
    r"|bukkake|creampie|deepthroat|xhamster|redtube|youporn|camgirl|stripper"
    r"|femboy"
    r"|\b(?:xxx|nude|nudes|naked|sex|sexy|erotic|erotica|boobs|tits|pussy"
    r"|dick|cock|penis|vagina|anal|cum|fetish|bdsm|bondage|escort|rape"
    r"|gore|beheading|snuff|trans)\b",
    re.IGNORECASE,
)


def is_inappropriate_image(result: dict) -> bool:
    """True when an image result's name — its title or any of its URLs —
    contains inappropriate content and it must not be shown or listed."""
    fields = (
        result.get("title", ""),
        result.get("image", ""),
        result.get("thumbnail", ""),
        result.get("url", ""),
    )
    return any(_NSFW_RE.search(str(f)) for f in fields if f)


def _search(kind: str, query: str, max_results: int, **kwargs) -> list[dict]:
    """Run one DDGS search of the given kind; return [] on any failure.
    Extra kwargs (e.g. safesearch) are dropped and the search retried when
    the installed ddgs version does not accept them."""
    try:
        with DDGS() as ddgs:
            method = getattr(ddgs, kind)
            try:
                results = method(query, max_results=max_results, **kwargs)
            except TypeError:
                if not kwargs:
                    raise
                results = method(query, max_results=max_results)
    except Exception:
        return []
    return results or []


def web_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    return _search("text", query, max_results)


def image_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    """Image search with DDGS safe search forced on; results whose title or
    URLs contain inappropriate terms are dropped before anyone (the terminal
    renderer or the model) sees them."""
    results = _search("images", query, max_results, safesearch="on")
    return [r for r in results if not is_inappropriate_image(r)]


def news_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    return _search("news", query, max_results)


def format_search_results(results: list[dict]) -> str:
    """Format text-search results into a readable block for the model."""
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        body = r.get("body", "No snippet")
        href = r.get("href", "")
        lines.append(f"[{i}] {title}\n    {body}\n    URL: {href}")
    return "\n\n".join(lines)


def format_image_results(results: list[dict]) -> str:
    """Format image results as text context for the model."""
    if not results:
        return "No images found."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        image_url = r.get("image", "")
        source = r.get("url", "")
        w, h = r.get("width", "?"), r.get("height", "?")
        lines.append(f"[{i}] {title} ({w}x{h})\n    Image: {image_url}\n    Source: {source}")
    return "\n\n".join(lines)


def format_news_results(results: list[dict]) -> str:
    """Format news results into a readable block for the model."""
    if not results:
        return "No news found."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        body = r.get("body", "No snippet")
        url = r.get("url", "")
        date = r.get("date", "")
        source = r.get("source", "")
        lines.append(f"[{i}] {title}\n    {source} · {date}\n    {body}\n    URL: {url}")
    return "\n\n".join(lines)
