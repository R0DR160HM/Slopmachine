"""DuckDuckGo search (text, image, news) and result formatting."""

from ddgs import DDGS

from pythia.config import DEFAULT_MAX_RESULTS


def _search(kind: str, query: str, max_results: int) -> list[dict]:
    """Run one DDGS search of the given kind; return [] on any failure."""
    try:
        with DDGS() as ddgs:
            results = getattr(ddgs, kind)(query, max_results=max_results)
    except Exception:
        return []
    return results or []


def web_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    return _search("text", query, max_results)


def image_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    return _search("images", query, max_results)


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
