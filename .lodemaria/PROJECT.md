Here's the comprehensive overview of the project, covering both its structure and key components:

### Overview

**Project Structure:**
- `build`: Entry point that uses `build.ps1` to build a self-contained single-file executable (`lodemaria.exe`).
  - Scripts inside this directory:
    - `setup.py`
    - `build.sh`
      - Code for the entry point and other utility functions.
    - `config.py` contains default model names, results count, and Ollama server setup.
    - `cli` contains command-line interface functionality.

- `lodemaria`: Main module that includes various helper scripts like `ChatSession`, `prompts`, `tools`, and more.
  - These contain functions for interacting with the user's messages, managing tools calls, parsing input, etc.

### Modules and Functions

1. **`lodemaria.tools`**:
   - Contains public export classes (`_eval_node`, `calculate`, `display_images`) and public methods (`parse_tool_call`).
   - Provides safe arithmetic evaluation via an AST based on user-provided inputs.
   - Handles fetching images, news, web page searches, etc.

2. **`lodemaria.cli`**:
   - Entry point for interacting with the Ollama model.
   - Contains helper functions (`stream_chat`, `ask`, `trim_messages`).
   - Main loop that handles user input and interactions with the model.

3. **`lodemaria/chat`**: 
   - A main script for direct command-line interaction.
   - Handles various command-line arguments for interaction with the model (e.g., query, results count).

4. **Other Components**:
   - `config.py`: Contains system-specific settings like model names and dependencies.
   - `prompts`: Defines commands to ask questions from the model and provide responses.

### Key Features

- **Chat Functionality**: Enables users to chat with an Ollama model through a series of prompts, interactions, and responses.
  - Uses a public helper script (`ChatSession`) for direct command-line interaction.
  
- **Model Management**: Allows easy interaction with various models like `llm`, `ollama install` (for automatic installation), and more.

### Usage

1. **Launching the Chat Session**:
   ```bash
   python -m lodemaria.chat
   ```

2. **User Input Handling**:
   - Supports input prompts, navigations through tools, and responses generation.
   - Example: `python -m lodemaria.chat --model quwen2.5 --results 10`
   - This example demonstrates using the main entry point (`ChatSession`).

3. **Command-Line Parameters (CLI)**:
   ```bash
   python -m lodemaria.cli
   ```

- **Dependencies**: Uses `argparse`, `json`, `lru-cache`, and others for command-line argument parsing.

### Example Usage:

```python
from lodemaria.chat import ChatSession

# Initialize the session with a specific model, max results, and ensure server is reachable.
chat = ChatSession(
    "llama2",
    100,
)

# Start the chat session.
chat.run()
```

This example shows how to interact with the Ollama model using the CLI.

### Important Notes

- This project assumes that `argparse` and other modules are installed, as they're not included in standard Python distributions like PyCharm, VSCode, or IDEs by default. You might need to install these packages via pip if you are not currently using one.

This documentation provides a comprehensive overview of the project's structure, key components, usage examples, dependencies, and best practices for interacting with the model.
