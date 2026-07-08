# lodemaria/chat.py

The interactive chat session: user input → (tools) → model → answer.

## Purpose and Role

This module manages the interactive chat experience with a large language model. It includes functions to handle user input, route commands, manage shell sessions, and execute tools on the server. The chat session ensures that user input is processed correctly, tool calls are handled efficiently, and the backend connection is managed gracefully.

## Public/Exported Classes, Functions, Constants, and Entrypoints

### ChatSession Class
- **Constructor**:
  - `__init__(self, model: str, max_results: int, ensure_server=None)`: Initializes the chat session with a specified model, maximum results per search, and an optional function to ensure the server is reachable.
- **run(self, initial_prompt: str = "") -> None**: Starts the chat loop, handling user input, routing commands, managing shell sessions, and executing tools.

### InputReader Class
- **start(self) -> None**: Start the interactive prompt reader.
- **allow(self) -> None**: Allow input to be processed by the reader.
- **lines.get(timeout=0.2)**: Get a line from the reader with a timeout.

### ShellManager Class
- **start(command: str, origin="user") -> Session**: Start a new shell session and focus it. Returns the session object.
- **terminate_all(self) -> None**: Terminate all active shell sessions.

### Message Class
- **role**: The role of the message (e.g., "user" or "assistant").
- **content**: The content of the message.

### parse_tool_call(assistant_text: str) -> dict or None**: Parse a tool call from the assistant's response.

### execute_tool_call(tool_call: dict, max_results: int) -> str**: Execute a tool on the model and return the result.

### display_images(img_results: list[Result]) -> None**: Display image results.
- **format_image_results(img_results: list[Result]) -> str**: Format image results for rendering.
- **image_search(term: str, max_results: int) -> list[Result]**: Search for images related to a term.
- **news_search(term: str, max_results: int) -> list[Result]**: Search for news articles related to a term.

### web_search(term: str, max_results: int) -> list[Result]**: Search for web pages related to a term.
- **parse_tool_call(assistant_text: str) -> dict or None**: Parse a tool call from the assistant's response.

### write_project_documentation() -> str**: Run the documentation writer and record its summary in the history.
- **ShellManager Class**
  - **start(command: str, origin="user") -> Session**: Start a new shell session and focus it. Returns the session object.
  - **terminate_all(self) -> None**: Terminate all active shell sessions.

### ChatSession Class
- **run(self, initial_prompt: str = "") -> None**: Starts the chat loop, handling user input, routing commands, managing shell sessions, and executing tools.
- **InputReader Class**
  - **start(self) -> None**: Start the interactive prompt reader.
  - **allow(self) -> None**: Allow input to be processed by the reader.
  - **lines.get(timeout=0.2)**: Get a line from the reader with a timeout.

### ShellManager Class
- **start(command: str, origin="user") -> Session**: Start a new shell session and focus it. Returns the session object.
- **terminate_all(self) -> None**: Terminate all active shell sessions.

### Message Class
- **role**: The role of the message (e.g., "user" or "assistant").
- **content**: The content of the message.

### parse_tool_call(assistant_text: str) -> dict or None**: Parse a tool call from the assistant's response.

### execute_tool_call(tool_call: dict, max_results: int) -> str**: Execute a tool on the model and return the result.

### display_images(img_results: list[Result]) -> None**: Display image results.
- **format_image_results(img_results: list[Result]) -> str**: Format image results for rendering.
- **image_search(term: str, max_results: int) -> list[Result]**: Search for images related to a term.
- **news_search(term: str, max_results: int) -> list[Result]**: Search for news articles related to a term.

### web_search(term: str, max_results: int) -> list[Result]**: Search for web pages related to a term.
- **parse_tool_call(assistant_text: str) -> dict or None**: Parse a tool call from the assistant's response.

### write_project_documentation() -> str**: Run the documentation writer and record its summary in the history.

This module provides robust support for an interactive chat experience with a large language model, including seamless handling of multiple tools, seamless integration with shell sessions, and efficient management of the backend connection.
