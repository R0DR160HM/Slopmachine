# lodemaria/tools/registry.py

This file contains the logic for detecting and executing tool calls emitted by a language model. It includes functions to parse tool call requests, execute specific tools, and handle responses.

## Public Functions

### `parse_tool_call(text: str) -> dict[str, Any] | None`

**Purpose:** Parses the text to identify if it contains a tool call. If found, returns the parsed JSON dictionary; otherwise, returns `None`.

**Parameters:**
- `text`: A string containing the model's response.

**Returns:** A dictionary representing the tool call or `None` if no valid tool call is detected.

### `execute_tool_call(call: dict[str, Any], max_results: int) -> str`

**Purpose:** Executes a parsed tool call and returns feedback to the language model.

**Parameters:**
- `call`: A dictionary containing the details of the tool call.
- `max_results`: An integer specifying the maximum number of results to return for search tools.

**Returns:** A string providing feedback about the executed tool call, suitable for further input from the model.

## Internal Functions

### `_run_web_search(call: dict, max_results: int) -> str`

Executes a web search based on the query provided in the tool call. Displays search results and returns a formatted string.

### `_run_image_search(call: dict, max_results: int) -> str`

Executes an image search based on the query provided in the tool call. Displays images and returns a formatted string.

### `_run_news_search(call: dict, max_results: int) -> str`

Executes a news search based on the query provided in the tool call. Displays news results and returns a formatted string.

### `_run_fetch_url(call: dict, max_results: int) -> str`

Fetches content from a URL specified in the tool call and returns it as plain text.

### `_run_calculate(call: dict, max_results: int) -> str`

Evaluates a mathematical expression provided in the tool call and returns the result as plain text.

### `_run_tool_forge(call: dict, max_results: int) -> str`

Forges a new tool based on a description provided in the tool call. Registers the new tool and provides instructions for its use.

### `_run_write_project_documentation(call: dict, max_results: int) -> str`

Writes documentation for the project to a file and returns a summary of the documentation process.

### `_run_forged_tool(call: dict, max_results: int) -> str`

Executes a previously forged tool based on the name provided in the tool call. Returns the result of the tool execution.

## Constants

### `_REQUIRED_KEYS: dict[str, tuple[str, ...]]`

A dictionary mapping tool names to tuples of required JSON keys for those tools.

### `_forged_tools: dict[str, ForgedTool]`

A dictionary that stores all forged tools by their names.

### `_JSON_OBJECT_RE: re.Pattern`

A regular expression pattern used to identify JSON objects within a string.

## Algorithm and Side Effects

- The `parse_tool_call` function searches for JSON objects in the input text, which indicates a tool call.
- Each tool execution function (`_run_web_search`, etc.) performs specific actions based on the tool name and parameters provided. For instance, `_run_image_search` calls an image search API and displays results using a custom function `display_images`.
- The `_forged_tools` dictionary keeps track of all tools that have been dynamically created. Each tool has a unique name to avoid conflicts with built-in tools.
- Error handling is performed within each tool execution function to manage exceptions that may occur during tool execution.

This unit provides a comprehensive system for handling tool calls, making it possible for the language model to interact with various functionalities through text-based commands.
