# lodemaria/llm.py

This Python module provides helpers for interacting with the Ollama model, including managing message history and streaming responses.

## Public Functions

### `strip_think(text: str) -> str`

- **Purpose**: Removes `` blocks from the given text.
- **Parameters**:
  - `text` (str): The input text containing `` blocks.
- **Return Value**: The text with `` blocks removed.

### `visible_text(partial: str) -> str`

- **Purpose**: Returns the portion of a partially-received response that is safe to display, removing completed `` blocks and hiding anything after an unclosed `` blocks and extract lists from model responses.
