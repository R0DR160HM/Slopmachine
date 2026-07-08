### lodemaria/cli.py

**Command-line entry point: argument parsing and Ollama server lifecycle.**

This module deliberately imports nothing from third-party packages at module level, so a missing dependency produces a friendly message instead of a traceback.

#### Class: ChatSession
##### Parameters:
- `model`: The Ollama model to use (default: `DEFAULT_MODEL`).
- `max_results`: Max search results per query (default: `DEFAULT_MAX_RESULTS`).
- `ensure_server`: A function that ensures the Ollama server is reachable before each interaction. If not provided, a default server start-up time and retry logic are used.

##### Behavior:
- Initializes the chat session with the specified model and maximum number of results.
- Manages the interaction loop, prompting the user for input, running queries, and handling responses.
- Exits gracefully when the user exits the chat session.

#### Class: ChatPrompt
##### Parameters:
- `user`: The user's name.
- `model`: The Ollama model to use (default: `DEFAULT_MODEL`).
- `max_results`: Max search results per query (default: `DEFAULT_MAX_RESULTS`).
- `ensure_server`: A function that ensures the Ollama server is reachable before each interaction. If not provided, a default server start-up time and retry logic are used.

##### Behavior:
- Initializes the chat prompt with the specified user name and model.
- Manages the initial chat session prompt, prompting the user for input, running queries, and handling responses.

#### Function: _check_dependencies()
##### Parameters: None
##### Behavior:
- Checks if all required packages (`ollama`, `ddgs`, `rich`) are installed. If not installed, it exits with a friendly message.

#### Function: _start_ollama_server()
##### Parameters: None
##### Behavior:
- Attempts to start the Ollama server and waits for it to become ready.
- Exits if the server fails to start within the specified retries.

#### Function: _server_reachable()
##### Parameters: None
##### Behavior:
- Checks if the Ollama server is reachable by attempting to access its API endpoint.
- Returns `True` if the server is reachable, otherwise `False`.

#### Function: _wait_reachable(retries=SERVER_LIST_RETRIES)
##### Parameters: `retries`: The number of retries before giving up (default: `SERVER_LIST_RETRIES`).
##### Behavior:
- Polls for the server to be reachable (`retries` times), waiting 0.5 seconds between each poll.
- Returns `True` if the server is reachable, otherwise `False`.

#### Function: _installed_models()
##### Parameters: None
##### Behavior:
- Lists all models currently installed on the Ollama server.
- Returns a set of canonicalized model tags.

#### Function: _canonical(name)
##### Parameters: `name`: The name of a model tag (either with or without colon).
##### Behavior:
- Canonicalizes the model tag, adding a colon if necessary to match the expected format.

#### Function: _ensure_models(chat_model)
##### Parameters: `chat_model`: The chat model to pull.
##### Behavior:
- Pulls the specified chat model and any other required models (megabrain and forge) from the Ollama server if they are not already installed.

#### Function: _unload_models()
##### Parameters: None
##### Behavior:
- Unloads all loaded models, freeing RAM/VRAM.

#### Function: _terminate_tree(proc)
##### Parameters: `proc`: The process to terminate.
##### Behavior:
- Terminates the specified process and its children by killing the entire tree.
- Uses different methods depending on whether the OS is Windows or not.

#### Function: _stop(proc)
##### Parameters: `proc`: The process to stop.
##### Behavior:
- Stops the specified process gracefully by waiting for it to exit (with a timeout), then kills the process if it does not exit within the timeout.
