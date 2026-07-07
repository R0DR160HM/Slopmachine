# Search Tools

The `search.py` file provides a set of utilities for performing searches using the DuckDuckGo search engine and formatting the results. This includes web, image, and news searches.

## Functions

### `_search(kind: str, query: str, max_results: int) -> list[dict]`

- **Purpose**: Runs a single DDGS search of the given kind.
- **Parameters**:
  - `kind`: The type of search ("text", "images", "news").
  - `query`: The search query string.
  - `max_results`: Maximum number of results to return (default is from config).
- **Return Value**: A list of search results or an empty list on failure.
- **Behavior**: Uses the `DDGS` class from the `ddgs` module to perform the search. Handles exceptions and returns an empty list if any error occurs.
- **Side Effects**: Makes network requests.

### `web_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]`

- **Purpose**: Perform a web search.
- **Parameters**:
  - `query`: The search query string.
  - `max_results`: Maximum number of results to return (default is from config).
- **Return Value**: A list of search results formatted as dictionaries.

### `image_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]`

- **Purpose**: Perform an image search.
- **Parameters**:
  - `query`: The search query string.
  - `max_results`: Maximum number of results to return (default is from config).
- **Return Value**: A list of search results formatted as dictionaries.

### `news_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]`

- **Purpose**: Perform a news search.
- **Parameters**:
  - `query`: The search query string.
  - `max_results`: Maximum number of results to return (default is from config).
- **Return Value**: A list of search results formatted as dictionaries.

### `format_search_results(results: list[dict]) -> str`

- **Purpose**: Format text-search results into a readable block for the model.
- **Parameters**:
  - `results`: A list of search results.
- **Return Value**: Formatted string with results in a human-readable format. If no results are found, returns "No results found."

### `format_image_results(results: list[dict]) -> str`

- **Purpose**: Format image results as text context for the model.
- **Parameters**:
  - `results`: A list of search results.
- **Return Value**: Formatted string with results in a human-readable format. If no images are found, returns "No images found."

### `format_news_results(results: list[dict]) -> str`

- **Purpose**: Format news results into a readable block for the model.
- **Parameters**:
  - `results`: A list of search results.
- **Return Value**: Formatted string with results in a human-readable format. If no news are found, returns "No news found."
