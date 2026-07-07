# Deep Research Mode

Deep research mode is a multi-phase autonomous research pipeline that processes user requests for in-depth investigation. It extracts the key topic from the request, gathers relevant information from web and news sources, generates an abstract, identifies subtopics, delves into each subtopic individually, synthesizes all findings, and concludes with images.

## Public Functions

### `run_deep_research(request: str, model: str, max_results: int) -> str`

**Parameters:**
- `request`: The user's input request for research.
- `model`: The language model to use for processing the request.
- `max_results`: Maximum number of results to fetch from search queries.

**Returns:** A string representing the final research report.

**Behavior:** This function orchestrates the entire deep research pipeline. It starts by extracting keywords from the user's request, performs a general search based on these keywords, writes an abstract from the overview, identifies subtopics from the abstract, dives into each subtopic to gather detailed information, synthesizes all findings into a cohesive report, and concludes with relevant images.

### `gather_research(query: str, max_results: int, do_news: bool = True) -> str`

**Parameters:**
- `query`: The search query.
- `max_results`: Maximum number of results to fetch from the web or news search.
- `do_news` (optional): Whether to include news search in addition to web search.

**Returns:** A string containing a formatted overview of the research, including text and/or news results.

**Behavior:** This function performs a web search for a given query and optionally includes news. It fetches the top links from the search results and extracts their full content. The fetched content is organized into sections and returned as a formatted string.

### `_ask_streamed(model: str, system: str, user: str, label: str) -> str`

**Parameters:**
- `model`: The language model to use for processing.
- `system`: System prompt for the model.
- `user`: User input for the model.
- `label`: A label for the message being processed.

**Returns:** Cleaned text from the streamed response of the language model.

**Behavior:** This function sends a user query to a specified language model and returns the cleaned text of its streamed response. It is used for phases where the output needs to be displayed in real-time, such as generating an abstract or final report.

## Internal Logic and Algorithms

- **Topic Extraction**: The `extract_topic` function cleans up the user's message to extract the main topic by removing brackets and replacing common phrases like "deep research" with just "research".
  
- **Focus Query**: The `_focus_query` function ensures that specific keywords are included in every search query, preventing searches from drifting to generic pages.

- **Multi-Phase Pipeline**: The `run_deep_research` function orchestrates the deep research pipeline through seven phases:
  1. Extract key keywords from the user's request.
  2. Perform a general text and news search based on these keywords.
  3. Write an abstract from the overview.
  4. Derive subtopics from the abstract.
  5. Dive into each subtopic to gather detailed information.
  6. Synthesize all findings into a cohesive report.
  7. Fetch relevant images to close the report.

- **Side Effects**: The function uses various utility functions and classes, such as `console` for printing output, `fetch_url` for fetching web pages, and `display_images` for displaying fetched images. It also interacts with language models via the `_ask_streamed` function, which handles real-time streaming of responses.

## Usage

To use the deep research mode, call the `run_deep_research` function with a user's request and specify the language model to use. The function will return the final research report as a string. This can be further processed or displayed in an interface.

```python
report = run_deep_research("What is the history of quantum computing?", "gpt-4", 5)
print(report)
```
