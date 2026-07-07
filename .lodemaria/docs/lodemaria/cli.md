# lodemaria/cli.py

This file is the command-line entry point for the `lodemaria` application. It handles argument parsing, manages the lifecycle of the Ollama server, and orchestrates the interaction with the user.

## Public Functions

### `_ollama_install_command()`

**Purpose:** Generates the command to install the Ollama server based on the operating system.

**Parameters:**
- None

**Return Value:** A list of strings representing the installation command.

**Behavior:** Checks if the operating system is Windows. If so, it returns a PowerShell command; otherwise, it returns a shell command for Unix-based systems.

### `_install_ollama()`

**Purpose:** Installs the Ollama server automatically using the official installer.

**Parameters:**
- None

**Return Value:** None

**Behavior:** Calls `_ollama_install_command()` to get the installation command and runs it using `subprocess.run()`. If the installer is missing or fails, exits with an error message.

### `_parse_args()`

**Purpose:** Parses command-line arguments.

**Parameters:**
- None

**Return Value:** An `argparse.Namespace` object containing the parsed arguments.

**Behavior:** Sets up an argument parser and defines the following options:
- `--model` or `-m`: Specifies the Ollama model to use.
- `--results` or `-r`: Specifies the maximum number of search results per query.
- `prompt`: An optional first prompt to send immediately.

### `_force_utf8_output()`

**Purpose:** Ensures that emoji-heavy output is displayed correctly in the console.

**Parameters:**
- None

**Return Value:** None

**Behavior:** Iterates over standard output and error streams. If a stream has a `reconfigure` method, it reconfigures it to use UTF-8 encoding with error replacement.

### `_check_dependencies()`

**Purpose:** Checks if all required dependencies are installed.

**Parameters:**
- None

**Return Value:** None

**Behavior:** Lists missing packages and exits with an error message if any are found. Uses `importlib.util.find_spec()` to check for package availability.

### `_start_ollama_server()`

**Purpose:** Starts the Ollama server.

**Parameters:**
- None

**Return Value:** A `subprocess.Popen` object representing the running Ollama server process.

**Behavior:** Checks if the `ollama` command is available. If not, calls `_install_ollama()` to install it. Then, starts the server in a detached mode and waits for it to initialize.

### `_installed_models()`

**Purpose:** Retrieves the list of installed models from the Ollama server.

**Parameters:**
- None

**Return Value:** A set of strings representing the installed model tags.

**Behavior:** Attempts to retrieve the list of models using the `ollama` Python module. If successful, returns a canonicalized set of model names. If the server does not respond within the specified retries, exits with an error message.

### `_canonical(name)`

**Purpose:** Canonicalizes a model name by appending ':latest' if it does not contain a version tag.

**Parameters:**
- `name`: The model name as a string.

**Return Value:** A canonicalized model name as a string.

**Behavior:** Checks if the model name contains a colon. If not, appends ':latest'.

### `_ensure_models(chat_model)`

**Purpose:** Ensures that all necessary models are downloaded and available.

**Parameters:**
- `chat_model`: The chat model to ensure is available.

**Return Value:** None

**Behavior:** Checks for the existence of the specified models (`chat_model`, `MEGABRAIN_MODEL`, `FORGE_MODEL`). If any are missing, downloads them using `ollama pull`. Exits with an error message if a download fails.

### `_unload_models()`

**Purpose:** Unloads all loaded models from the Ollama server to free up memory and VRAM.

**Parameters:**
- None

**Return Value:** None

**Behavior:** Uses the `ollama` Python module to unload all loaded models. This ensures that any previously running instances of the server do not retain their models after the current session ends.

### `_stop(proc)`

**Purpose:** Stops the Ollama server process and cleans up resources.

**Parameters:**
- `proc`: A `subprocess.Popen` object representing the Ollama server process.

**Return Value:** None

**Behavior:** Calls `_unload_models()` to unload all models. Terminates the process using `terminate()`. Waits for the process to terminate gracefully; if it does not, kills it with a timeout of 5 seconds.

### `main()`

**Purpose:** The main entry point for the command-line interface.

**Parameters:**
- None

**Return Value:** None

**Behavior:** Calls `_force_utf8_output()` to ensure UTF-8 encoding. Parses arguments using `_parse_args()`, checks dependencies with `_check_dependencies()`, and imports necessary modules within a try block to avoid circular import issues. Starts the Ollama server, ensures models are available, runs the chat session, and finally stops the server using `_stop()`.

This function orchestrates the entire flow of the application, from starting the server and ensuring model availability to handling user input and cleaning up resources when the session ends.
