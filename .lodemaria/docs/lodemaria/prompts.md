# System Prompts for Chat Assistant and Deep-Research Pipeline

This module contains system prompts and instructions designed to guide the behavior of various AI agents within a chat assistant and deep-research pipeline. The primary goal is to ensure that each agent operates within specific constraints, performs tasks efficiently, and adheres to predefined rules.

## Constants
- **DEEP_SUBTOPICS**: An integer representing the number of subtopics to generate during deep research.

## Prompts

### SYSTEM_PROMPT_TEMPLATE
A template for the system prompt for the chat assistant. This prompt outlines the role and capabilities of the assistant, including the use of tools, rules for behavior, and specific instructions on how to respond when calling a tool.

- **Parameters**: `now` (current date and time)
- **Behavior**: Generates a JSON block that describes which tool to call or provides direct text answers based on the user's request.
- **Notable Logic**: Enforces strict rules such as never mentioning being an AI, using specific tools for certain tasks like image searches, and handling input gracefully.

### FORGE_SYSTEM_PROMPT
A system prompt for a code generation model. This model is tasked with creating new Python tools based on the user's description.

- **Behavior**: Responds with a single Python code block containing the tool name, description, and entry point function.
- **Notable Logic**: Ensures that the generated tool adheres to strict rules, including using only the standard library and handling malformed input gracefully.

### DOC_FILE_SYS
A system prompt for a documentation writer model. This model generates markdown documentation for a single file or group of files.

- **Behavior**: Writes clear and comprehensive documentation in markdown format, describing each public/exported class, function, constant, and entry point.
- **Notable Logic**: Ensures that the documentation is structured and informative, providing details on internal logic, side effects, and notable aspects like network requests or global state changes.

### DOC_PROJECT_SYS
A system prompt for a project documentation writer model. This model generates comprehensive documentation for an entire software project based on markdown documentation of individual files.

- **Behavior**: Writes one cohesive document that outlines the project's overview, architecture, key concepts, and setup/usage instructions.
- **Notable Logic**: Ensures that the documentation is well-structured and informative, avoiding the inclusion of invented details not present in the material.

### MEGABRAIN_REWRITE_SYS
A system prompt for a prompt rewriter. This model rewrites user messages into clear, well-structured prompts for AI agents.

- **Behavior**: Rewrites the user's message to make the goal, context, and expected response format explicit.
- **Notable Logic**: Ensures that the rewritten prompt is in English, faithfully preserves the original intent, and adheres to specific rules like removing mentions of "megabrain".

### DEEP_RESEARCH_PHASE_PROMPTS
Prompts for the deep-research phase of tasks. These prompts guide the assistant through extracting keywords, generating abstracts, proposing subtopics, synthesizing information, and suggesting image searches.

- **Behavior**: Generates relevant data based on the user's research queries.
- **Notable Logic**: Ensures that each subtopic is directly tied to the main topic and contains the necessary keywords.
