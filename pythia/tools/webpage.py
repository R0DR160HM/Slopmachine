"""Fetch a web page and extract its readable text."""

import html
import re
import urllib.request

FETCH_TIMEOUT = 15
MAX_DOWNLOAD_BYTES = 2_000_000
DEFAULT_MAX_CHARS = 4000
USER_AGENT = "Mozilla/5.0 (Lodemar.IA bot)"


def extract_text(html_text: str) -> str:
    """Extract readable text from HTML. Uses BeautifulSoup if available, else regex."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "noscript", "head", "header",
                         "footer", "nav", "svg", "form"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
    except ImportError:
        # Fallback: strip tags with regex
        no_scripts = re.sub(
            r"<(script|style|noscript)[^>]*>.*?</\1>", "",
            html_text, flags=re.DOTALL | re.IGNORECASE,
        )
        text = html.unescape(re.sub(r"<[^>]+>", " ", no_scripts))
    # Collapse blank lines and surrounding whitespace
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def fetch_url(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Download a web page and return its visible text, truncated to max_chars."""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read(MAX_DOWNLOAD_BYTES)
        text = extract_text(raw.decode(charset, errors="replace"))
    except Exception as e:
        return f"Failed to fetch {url}: {e}"

    if not text:
        return f"No readable text found at {url}."
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…[conteúdo truncado]"
    return text
