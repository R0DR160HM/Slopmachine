"""Tools the model (and the deep-research pipeline) can invoke."""

from lodemaria.tools.calculator import calculate
from lodemaria.tools.display import display_images
from lodemaria.tools.documentation import write_project_documentation
from lodemaria.tools.registry import execute_tool_call, parse_tool_call
from lodemaria.tools.search import (
    format_image_results,
    format_news_results,
    format_search_results,
    image_search,
    news_search,
    web_search,
)
from lodemaria.tools.webpage import fetch_url

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
    "parse_tool_call",
    "web_search",
    "write_project_documentation",
]
