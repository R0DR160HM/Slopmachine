The interactive chat session in Lodemaria enables users to interact with a sophisticated language model through a series of tools and commands. The session includes user input, navigates between different prompts, executes tools, and receives feedback on their interactions. Here's a detailed documentation for the `ChatSession` class:

### **Class Summary**

The `ChatSession` class encapsulates a full interactive chat experience: users can input text, navigate through available tools, interact with the model, and receive feedback on their responses.

**Key Features of the Class:**

1. **Initialization:** The session starts by initializing with the specified model, maximum number of results, and whether to ensure the Ollama server is reachable.
2. **User Input Handling:** Users can input messages, which are processed based on the specified rules (e.g., image search or news search).
3. **Model Call Management:** After each input, a new tool call is initiated. The model responds with a feedback message and updates the session status accordingly.
4. **Feedback Reception:** The model provides a summary of its output as part of its response.

### **Methods**

#### `run(self, initial_prompt: str = "")`

- **Purpose:** Initializes the chat session, allowing interaction and managing user input.
- **Parameters:**
  - `initial_prompt`: Optional prompt to start with. If not provided, the session starts with a simple "quit" message.
- **Returns:**
  - No return value.

#### `_stream_assistant(self)`

- **Purpose:** Continuously stream one assistant turn, transparently (re)starting the Ollama server and retrying once if the backend connection drops.
- **Parameters:**
  - `return`: The result of the current tool call, which is used for summary generation.

#### `_agent_loop(self)`

- **Purpose:** Main loop to handle user input and interactions with the model.
- **Parameters:**
  - No parameters.
- **Returns:**
  - No return value.

### **Usage**

To use this class, you can start by creating an instance of `ChatSession` and calling its methods as needed. For example:

```python
from lodemaria.chat import ChatSession

# Initialize the session with a default model, max results, and ensure server is reachable
chat = ChatSession(
    MEGABRAIN_MODEL,
    100,
    # Ensure the Ollama server is reachable
)

# Main loop to handle user input and interactions with the model
chat.run()
```

This setup allows users to engage in interactive conversations, manage their preferences, and interact with a sophisticated language model through the chat experience.
