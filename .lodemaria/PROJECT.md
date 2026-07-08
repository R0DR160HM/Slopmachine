# Lodemaria Project Documentation

## Overview
Lodemar.IA is a Python package designed for interacting with the Ollama model, an AI capable of text-based interactions and web searches. The project comprises several modules that facilitate different functionalities such as command-line interaction, deep research mode, tool management, file documentation generation, and more.

### Entry Point: Lodemaria
The primary entry point for the Lodemaria package is the `lodemaria.py` script. This script can be executed directly to run various commands provided by the package. It supports one or no parameters, depending on the specific command being used.

#### Public/Exported Classes and Functions

- **`CLI`:**
  - Responsible for parsing arguments passed during execution.
  
- **`main`:**
  - Initializes the application and calls `CLI.parse_args()` to handle user inputs efficiently.

### Module-Level Function and Entry Point
The module-level function, `main()`, initializes Lodemaria by executing the CLI entry point (`CLI.main()`). If no specific command is provided, it defaults to a help message. 

#### Internal Logic

- **Chat Session Management:**
  - The main functionality for initiating chat sessions with the model is handled by the `ChatSession` class.

- **System Prompts:**
  - System prompts are managed via the `DEEP_SUBTOPICS`, `SYSTEM_PROMPT_TEMPLATE`, and related configurations to guide user queries in a structured manner.

### Configuration
The package relies on configuration files stored in `lodemaria/config.py`. This file contains constants that define model settings, such as default models for different contexts, maximum results per query, and other relevant options. 

## Architecture
Lodemar.IA is composed of several major components:

- **CLI Module:** Manages command-line interaction with the Lodemaria package.
- **Chat Session Management:** Handles live chat sessions with user input and responses from the Ollama model.
- **Tool Execution:** Provides a framework for executing various tools available within the system, such as fetching web pages or performing calculations.
- **Deep Research Mode:** A specialized mode that performs multi-phase research operations to provide comprehensive and in-depth answers.

### Key Concepts and Flows
For new developers, understanding these key concepts is crucial:

1. **CLI (Command Line Interface)**
   - The `cli.py` module provides command-line entry points for interacting with the package.
   
2. **Chat Sessions**
   - Lodemaria facilitates live chat sessions where users can query the Ollama model and receive responses.

3. **Tools and Webpages**
   - Tools are used to perform specific tasks such as fetching web pages, performing calculations, or executing custom Python code. The system supports these tools seamlessly.
   
4. **Deep Research Mode**
   - This feature enables the generation of detailed research reports based on user queries by leveraging multiple steps, each informed by feedback from the model.

### Entry Points and Setup Instructions
To set up Lodemaria:

1. Ensure that all required dependencies (e.g., ollama, ddgs, rich) are installed.
2. Execute the `lodemaria.py` script to start the package with or without specific command-line arguments.

## Documentation for Specific Modules

### lodemaria/chat
- The `chat.py` file contains classes and functions necessary for managing chat sessions between users and the AI model.
- It includes functionality for handling user inputs, routing commands, managing shell sessions, and executing tools from a list of available options.

### lodemaria/tools/forge
- The tool forge module allows dynamically generating new tools based on descriptions provided by the model, which enhances the capabilities of the system dynamically.

### lodemaria/tools/search
- This module handles web search functionality. It leverages DuckDuckGo to perform searches and extracts readable text content from HTML pages using BeautifulSoup or regular expressions for stripping unwanted tags and entities.

## Conclusion

Lodemar.IA is a comprehensive tool for integrating language models like Ollama into applications, providing robust support for live chat sessions, versatile tool execution, and powerful research capabilities. Understanding the architecture and key components of this project will enable developers to effectively use it in their own projects.
