# Overview of Lodemaria Project

Lodemaria is a comprehensive Python-based application designed to provide interactive chat sessions, deep-research capabilities, and utility tools through a command-line interface. The project integrates various modules and services to deliver rich functionalities such as web searches, image fetching, news aggregation, tool execution, and dynamic documentation generation.

## Architecture Overview

### Major Modules/Areas
1. **Build Scripts**: Handle the creation of standalone executables for both Windows and Linux.
2. **Main Application (`lodemaria.py`)**: Serves as the entry point and orchestrator of the application's logic.
3. **Command-Line Interface (CLI) (`cli.py`)**: Manages argument parsing, server lifecycle, and interaction with the user.
4. **Chat Session Management (`chat.py`)**: Handles chat interactions, invokes tools, and processes responses from a language model.
5. **Tools Execution (`tools` module)**: Provides utilities for performing calculations, fetching images or web pages, executing tool calls, and writing documentation.
6. **Search Tools (`search` module)**: Implements search functionalities such as web searches, image searches, and news aggregations.
7. **Configuration Settings (`config.py`)**: Contains static configuration settings essential for the application's operation.

### Interactions
- The `lodemaria.py` script initiates the chat session by importing necessary modules and calling appropriate functions.
- Commands and arguments passed to the CLI are processed, starting the Ollama server and ensuring models are available.
- The `chat.py` module manages the conversation flow, invoking tools based on user inputs, and presenting responses through a live streaming mechanism.
- Tools in the `tools` and `search` modules interact with external services (e.g., web APIs) to gather information or perform tasks, which are then integrated into the chat session.

## Key Concepts and Flows

1. **Chat Session Initialization**:
   - The `main()` function from `lodemaria.py` is called.
   - CLI arguments are parsed to determine initial parameters like model selection and prompt messages.
   
2. **Model Loading and Interaction**:
   - Ollama server processes are managed using the `cli.py` module, starting with checking dependencies and downloading models if necessary.
   - The chat session is initialized in `chat.py`, handling user input through a live streaming mechanism.

3. **Tool Execution Flow**:
   - Tools in the `tools` directory (e.g., calculations, web/image searches) are invoked based on commands received during the chat session.
   - Responses from tools or external APIs are formatted and displayed to users in real-time.

4. **Documentation Generation**:
   - The `documentation.py` module hashes files and uses a language model to generate comprehensive project documentation.
   
## Setup/Usage Instructions

### Prerequisites
- Install Python 3.x.
- Ensure necessary dependencies are installed by running:
  ```sh
  pip install -r requirements.txt
  ```

### Building the Application
1. **Windows**:
   - Open PowerShell and navigate to the project directory.
   - Run `.\build.ps1`.
2. **Linux**:
   - Open a terminal and navigate to the project directory.
   - Run `./build.sh`.

### Running the Application
- Use the following command in your terminal:
  ```sh
  python -m lodemaria [optional arguments]
  ```
- Optional arguments include:
  - `-m MODEL`: Specifies the Ollama model to use.
  - `-r RESULTS`: Maximum number of search results per query.
  - `prompt` (optional): An initial prompt for the session.

### Example Usage
```sh
python -m lodemaria --model qwen2.5:0.5b --results 10 "What is quantum computing?"
```

This example command initializes a chat session using the specified model and settings, providing an initial query about quantum computing.

## Conclusion

Lodemaria combines robust backend services with user-friendly front-end interactions to provide dynamic and interactive experiences through text-based interfaces. The modular design ensures flexibility in integrating additional tools and enhancing functionality as needed.
