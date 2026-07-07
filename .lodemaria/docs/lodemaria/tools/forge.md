# `tool_forge.py`

This module provides a tool for dynamically generating and loading Python tools at runtime based on an agent's description. It interacts with a coder model to receive a Python module that defines the tool, loads it, and makes it callable by the agent.

## Public/Exported Classes

### `ForgedTool`
A data class representing a forged tool.

**Attributes:**
- `name` (`str`): The name of the tool.
- `description` (`str`): A description of the tool.
- `run` (`Callable[[str], str]`): The function that implements the tool's behavior. It takes a string input and returns a string output.
- `code` (`str`): The generated code for the tool.

## Public/Exported Functions

### `_extract_code(text: str) -> str`
Extracts Python code from a given text, expecting it to be enclosed in a markdown code block.

**Parameters:**
- `text` (`str`): The text containing the code block.

**Returns:**
- `code` (`str`): The extracted Python code.

**Raises:**
- `ForgeError`: If no code block is found or the extracted code does not contain a valid function definition for `run`.

### `_normalize_name(raw_name: object) -> str`
Normalizes a name to be a valid Python identifier by replacing invalid characters with underscores.

**Parameters:**
- `raw_name` (`object`): The raw name to normalize.

**Returns:**
- `name` (`str`): A normalized, valid Python identifier name.

### `forge_tool(description: str) -> ForgedTool`
Asks the coder model to build a tool based on the provided description and loads it.

**Parameters:**
- `description` (`str`): The description of the tool to be generated.

**Returns:**
- `tool` (`ForgedTool`): A `ForgedTool` object representing the generated tool.

**Raises:**
- `ForgeError`: If the response from the coder model does not contain a code block, the code fails to load, or the `run()` function contract is not met.
