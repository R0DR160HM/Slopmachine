# streaming.py

This module provides functionality for live token-by-token rendering of model responses, typically used in a terminal environment. It streams the response into a transient rich Live region rendered as Markdown, allowing users to watch the answer being written in real-time.

## Functions

### tail_view(text: str, width: int, max_rows: int) -> str

#### Parameters
- `text` (str): The input text from which to extract the trailing portion.
- `width` (int): The maximum width of a line before it is wrapped.
- `max_rows` (int): The maximum number of rows that can be displayed in the Live region.

#### Returns
- str: The trailing portion of the input text that fits within the specified dimensions.

#### Behavior
This function calculates the tail of the input text that would fit within a terminal window with the given width and maximum rows. It handles line wrapping, code fences, and ensures that the visible part of the text remains intact by re-opening any cut-off code blocks.

### stream_markdown(label: str, *, header: str | None = None, suppress_json: bool = False, **chat_kwargs) -> str

#### Parameters
- `label` (str): The label for the chat session.
- `header` (str | None): Optional rich markup to display above the streaming text. Defaults to `None`.
- `suppress_json` (bool): If `True`, suppresses any JSON or code fence responses, indicating a likely tool call. Defaults to `False`.
- **chat_kwargs**: Additional keyword arguments passed to the `stream_chat` function.

#### Returns
- str: The raw full text of the streamed response.

#### Behavior
This function streams a chat response token-by-token using the `stream_chat` function and renders it live in a transient rich Live region. It handles hiding the input prompt, calculating the visible part of the response, and updating the Live region accordingly. If `suppress_json` is enabled, it suppresses any responses that begin with "{" or a code fence, indicating a potential tool call.

#### Error Handling
- The function ensures that the Live region is properly started and stopped using a try-finally block.
- Any errors during the streaming process are caught, and the Live region is cleaned up before re-raising the exception.
