# lodemaria/tools/search.py

This file contains the `search.py` module, which is responsible for running DuckDuckGo searches and formatting the results for a machine learning model. The module includes four functions: `web_search`, `image_search`, `news_search`, and `format_search_results`.

### web_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]

Runs a text search using DuckDuckGo. Parameters:
- `query`: The search query.
- `max_results`: Maximum number of results to return (default is 10).

Returns:
- A list of dictionaries containing information about each result, including title, body, and URL.

### image_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]

Runs an image search using DuckDuckGo. Parameters:
- `query`: The search query.
- `max_results`: Maximum number of results to return (default is 10).

Returns:
- A list of dictionaries containing information about each result, including title, image URL, source, and dimensions.

### news_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]

Runs a news search using DuckDuckGo. Parameters:
- `query`: The search query.
- `max_results`: Maximum number of results to return (default is 10).

Returns:
- A list of dictionaries containing information about each result, including title, body, URL, date, and source.

### format_search_results(results: list[dict]) -> str

Formats a list of search results into a readable block for the machine learning model. Each dictionary in the list contains keys such as `title`, `body`, `href`, etc., which are then formatted into text context for the model.

This module is designed to help the model generate relevant and informative responses based on user queries.
