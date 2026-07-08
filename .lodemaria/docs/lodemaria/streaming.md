# Live Token-by-Token Rendering of Model Responses

The `lodemaria/streaming.py` file provides a function `stream_markdown()` that streams one chat response, rendering it live within a transient rich Live region. The user watches the answer being written and can interact with the prompt using keystrokes.

### Function Parameters
- `label`: A string used as an identifier for the chat session.
- `header` (optional): Rich markup to be shown above the streaming text inside the transient region. Defaults to `None`.
- `suppress_json` (optional): Boolean to suppress JSON responses that start with "{" or a code fence, which are considered tool calls and not displayed to the user. Defaults to `False`.
- Additional keyword arguments: Passes through to `lodemaria.llm.stream_chat()` for configuration.

### Function Behavior
1. **Streaming Response**: The response is streamed into a transient rich Live region rendered as Markdown. When the response completes, the region is erased and the caller prints the definitive rendering (or nothing if no output).
2. **Internal Logic**:
   - `tail_view(text: str, width: int, max_rows: int)`: Trims the trailing portion of `text` that fits in ~`max_rows` rendered rows. If the content outgrows the screen, it shows a sliding window of its tail.
   - `stream_markdown(label: str, *, header: str | None = None, suppress_json: bool = False, **chat_kwargs)`: Streams one chat response, rendering it live within a transient rich Live region. The function handles suppression of JSON responses and hides the bottom input prompt during streaming.

### Example Usage
```python
response = stream_markdown("Chat with ChatGPT", header="User:", suppress_json=True)
console.print(response)
```

This code snippet demonstrates how to use the `stream_markdown()` function to receive live updates from a model, handle JSON responses, and control the visibility of the bottom input prompt.
