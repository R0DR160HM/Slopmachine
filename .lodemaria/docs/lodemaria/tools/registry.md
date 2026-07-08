# lodemaria/tools/registry.py

The `registry.py` file in the `lodemaria/tools` directory is responsible for handling tool calls emitted by the model. It parses these JSON objects to determine which tool should be executed and returns the corresponding feedback message.

### Purpose and Role

This module ensures that the model can interact with various tools available within the system, such as web searches, image downloads, news articles, fetching websites, and performing mathematical calculations. It also handles forged tools created at runtime and provides clear instructions on how to use them.

### Public/Exported Classes, Functions, Constants, and Entry Point

#### `_REQUIRED_KEYS`

This dictionary maps tool names to tuples of required JSON keys. Each tool call should include these keys to ensure proper execution.

```python
# lodemaria/tools/registry.py
_REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "web_search": ("query",),
    "image_search": ("query",),
    "news_search": ("query",),
    "fetch_url": ("url",),
    "calculate": ("expression",),
    "tool_forge": ("description",),
    "shell": ("command",),
}
```

#### `_forged_tools`

This dictionary stores forged tools created at runtime. Each tool takes a single "input" string as an optional parameter.

```python
# lodemaria/tools/registry.py
_forged_tools: dict[str, ForgedTool] = {}
```

#### `parse_tool_call(text: str) -> dict[str, Any] | None`

This function searches for a JSON object anywhere in the (cleaned) response and parses it. It handles optional `` blocks to account for Qwen3 thinking mode.

```python
# lodemaria/tools/registry.py
def parse_tool_call(text: str) -> dict[str, Any] | None:
    # ...
```

#### `_run_web_search(call: dict, max_results: int) -> str`

This function handles the execution of a web search tool. It takes a query and displays the results to the user.

```python
# lodemaria/tools/registry.py
def _run_web_search(call: dict, max_results: int) -> str:
    # ...
```

#### `_run_image_search(call: dict, max_results: int) -> str`

This function handles the execution of an image search tool. It takes a query and displays the images to the user.

```python
# lodemaria/tools/registry.py
def _run_image_search(call: dict, max_results: int) -> str:
    # ...
```

#### `_run_news_search(call: dict, max_results: int) -> str`

This function handles the execution of a news search tool. It takes a query and displays the results to the user.

```python
# lodemaria/tools/registry.py
def _run_news_search(call: dict, max_results: int) -> str:
    # ...
```

#### `_run_fetch_url(call: dict, max_results: int) -> str`

This function handles the execution of a fetch URL tool. It takes a URL and displays the content to the user.

```python
# lodemaria/tools/registry.py
def _run_fetch_url(call: dict, max_results: int) -> str:
    # ...
```

#### `_run_calculate(call: dict, max_results: int) -> str`

This function handles the execution of a calculate tool. It takes an expression and displays the result to the user.

```python
# lodemaria/tools/registry.py
def _run_calculate(call: dict, max_results: int) -> str:
    # ...
```

#### `_run_tool_forge(call: dict, max_results: int) -> str`

This function handles the execution of a tool forge. It takes a description and executes it to create a new forged tool.

```python
# lodemaria/tools/registry.py
def _run_tool_forge(call: dict, max_results: int) -> str:
    # ...
```

#### `_run_shell_unavailable(call: dict, max_results: int) -> str`

This function handles the execution of the shell tool. It provides a fallback for when the shell tool is not available in the interactive chat session.

```python
# lodemaria/tools/registry.py
def _run_shell_unavailable(call: dict, max_results: int) -> str:
    # ...
```

#### `_run_forged_tool(call: dict, max_results: int) -> str`

This function handles the execution of a forged tool. It takes a tool name and executes it to return the result.

```python
# lodemaria/tools/registry.py
def _run_forged_tool(call: dict, max_results: int) -> str:
    # ...
```

#### `_HANDLERS`

This dictionary maps tool names to their corresponding execution handlers.

```python
# lodemaria/tools/registry.py
_HANDLERS: dict[str, Callable[[dict, int], str]] = {
    "web_search": _run_web_search,
    "image_search": _run_image_search,
    "news_search": _run_news_search,
    "fetch_url": _run_fetch_url,
    "calculate": _run_calculate,
    "tool_forge": _run_tool_forge,
    "shell": _run_shell_unavailable,
}
```

#### `execute_tool_call(call: dict[str, Any], max_results: int) -> str`

This function executes a parsed tool call and returns the feedback message for the model. It delegates the execution to the corresponding handler based on the tool name.

```python
# lodemaria/tools/registry.py
def execute_tool_call(call: dict[str, Any], max_results: int) -> str:
    # ...
```

### Notable Internal Logic, Algorithms, and Side Effects

The module handles various tools such as web searches, image downloads, news articles, fetching websites, and performing mathematical calculations. It also includes forged tools created at runtime to enhance the model's capabilities.

- **Tool Execution**: The `execute_tool_call` function delegates the execution of a parsed tool call to the corresponding handler based on the tool name.
- **Forged Tools**: The `_forged_tools` dictionary stores forged tools created at runtime, and the `_run_forged_tool` function handles their execution.
- **Error Handling**: All tools include error handling mechanisms to manage potential issues during execution.

### Conclusion

The `registry.py` file in the `lodemaria/tools` directory is a crucial component of the model's tool ecosystem. It parses JSON objects to determine which tool should be executed and returns the corresponding feedback message. The module includes various tools such as web searches, image downloads, news articles, fetching websites, and performing mathematical calculations. Additionally, it handles forged tools created at runtime to enhance the model's capabilities.
