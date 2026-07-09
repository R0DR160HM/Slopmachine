# Command-line entry point: argument parsing and Ollama server lifecycle.

This module deliberately imports nothing from third-party packages at module level, so a missing dependency produces a friendly message instead of a traceback.
**Purpose:** This module provides command-line interface for interacting with an Ollama model that can search the web. It includes functions to install Ollama automatically, handle dependencies, parse arguments, and perform server management tasks.

**Role in the project:**
- **Automatic installation:** Automatically downloads the latest version of Ollama.
- **Dependency checking:** Ensures all required packages are installed.
- **Argument parsing:** Parses command-line arguments for model name, results count, and model selection.
- **Server lifecycle:** Manages the server, including starting it and ensuring it starts after each run.

**Notable internal logic:**
1. **Install Ollama automatically:** Uses the `ollama install` command to download the latest version of Ollama if not already available.
2. **Check dependencies:** Ensures all required packages are installed.
3. **Argument parsing:** Parses command-line arguments for model name, results count, and model selection.
4. **Server lifecycle:** Manages the server, including starting it and ensuring it starts after each run.

**When several companion files are given:**
- The documentation is grouped together as ONE unit to simplify management and reuse across different projects.
