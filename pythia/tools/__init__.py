"""Tools the model (and the deep-research pipeline) can invoke."""

from pythia.tools.calculator import calculate
from pythia.tools.display import display_images
from pythia.tools.documentation import write_project_documentation
from pythia.tools.registry import execute_tool_call, parse_tool_calls
from pythia.tools.search import (
    format_image_results,
    format_news_results,
    format_search_results,
    image_search,
    news_search,
    web_search,
)
from pythia.tools.webpage import fetch_url

__all__ = [
    "calculate",
    "display_images",
    "execute_tool_call",
    "fetch_url",
    "format_image_results",
    "format_news_results",
    "format_search_results",
    "image_search",
    "news_search",
    "parse_tool_calls",
    "web_search",
    "write_project_documentation",
]
