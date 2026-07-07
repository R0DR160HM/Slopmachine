# lodemaria/chat.py

The `chat.py` file is the core module for managing an interactive chat session. It handles user input, invokes various tools and services (like web search, image search, news search), and processes responses using a language model.

## Public/Exported Classes and Functions

### pre_search_brackets(user_input: str, max_results: int) -> tuple[str, str]

**Purpose**: For each `[term]` in `user_input`, run searches before involving the model. Handles image search, news search, and text search.

- **Parameters**:
  - `user_input`: The user's input string containing possible terms to search.
  - `max_results`: Maximum number of results to fetch for each search type.

- **Returns**: A tuple consisting of a cleaned prompt (with brackets removed) and a search context string containing the results of the searches.

### ChatSession(model: str, max_results: int)

**Purpose**: Manages one interactive session. Owns the message history and the input reader.

- **Parameters**:
  - `model`: The initial language model to use.
  - `max_results`: Maximum number of results to fetch for each search type in a single session.

#### Methods

- **run(initial_prompt: str = "") -> None**

  **Purpose**: Runs the chat session, processing user input and generating responses.

  - **Parameters**:
    - `initial_prompt`: An optional initial prompt passed on the command line.

- **_print_header() -> None**

  **Purpose**: Prints a header for the chat session in the console.

- **_loop() -> None**

  **Purpose**: Main loop that continuously processes user input and generates responses until the session is terminated.

- **_handle_message(user_input: str) -> None**

  **Purpose**: Handles processing of a single message, including triggering Megabrain mode or deep research, performing searches, and generating responses using tools.

- **_activate_megabrain(user_input: str) -> str**

  **Purpose**: Switches to the Megabrain model, rewrites the prompt in a more structured form (Megabrain mentions removed), and handles an empty message as a last-resort fallback.

  - **Returns**: The rewritten prompt or an empty string if the message was empty after removing Megabrain references.

- **_agent_loop() -> None**

  **Purpose**: Manages the agent loop where the language model calls tools until it produces a final plain-text answer. Handles reaching the maximum number of tool-call iterations without a final answer.

### Internal Logic and Algorithms

1. **Search Handling**: The `pre_search_brackets` function parses user input for bracketed terms (e.g., `[term]`) and performs text, image, and news searches accordingly.
2. **Megabrain Mode Activation**: When the keyword "mega brain" is detected in the input, it switches to the Megabrain model and rewrites the prompt for more structured handling.
3. **Deep Research Trigger**: The `pre_search_brackets` function also detects a deep research trigger (e.g., "pesquisa profunda") and initiates a multi-phase autonomous research pipeline.

### Notable Internal Logic

- **Tool Execution**: The `_agent_loop` method continuously invokes tools until a plain-text answer is generated or the maximum number of tool calls is reached.
- **Error Handling**: The loop in `_agent_loop` handles exceptions that might occur during tool execution, ensuring the session can continue running.

This module forms the backbone of the interactive chat functionality, integrating various tools and services to provide intelligent responses to user queries.
