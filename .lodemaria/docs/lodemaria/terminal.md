### **File: lodemaria/terminal.py**

**Description:** This module provides thread-safe terminal I/O for a chat application. It handles both input from the user and output to the console in real-time, ensuring that messages are displayed correctly even when other threads are active.

#### **Public Exported Classes and Functions:**

- **`PromptArea`**: Manages the bottom-of-screen input area, including handling typed characters, backspace keys, and status updates. It ensures that the prompt is always visible by keeping track of its position in the console.
  - **Methods**:
    - `begin_input()`: Starts accepting input from the user.
    - `type_char(ch: str)`: Adds a single character to the input buffer.
    - `backspace()`: Removes the last character from the input buffer if possible.
    - `submit()`: Submits the current line of input and returns it. If Ctrl+C is pressed, it submits the line as an interrupt signal.
    - `deactivate()`: Hides the prompt area, preventing further input until shown again.

- **`SafeConsole`**: Extends the `Console` class to ensure that the prompt area stays visible while processing user input.
  - **Methods**:
    - `print(*args, **kwargs)`: Prints text to the console, erasing and redrawing the prompt area as necessary.

- **`InputReader`**: Manages the background thread responsible for reading user input from the terminal.
  - **Methods**:
    - `start()`: Starts the input reader thread.
    - `allow()`: Opens the prompt area for the next line of input.
    - `_run()`: The main loop for the input reader thread, handling typed characters, backspace keys, and status updates. It also handles EOF/Ctrl+D and Ctrl+C signals by submitting them to the chat loop.

#### **Internal Logic, Algorithms, and Side Effects:**

- **Input Handling**:
  - The `InputReader` reads user input character-by-character using a background thread.
  - It keeps track of the current line being typed and updates it as characters are entered.
  - When a Ctrl+C is pressed, the `InputReader` submits an interrupt signal to the chat loop.

- **Prompt Management**:
  - The `PromptArea` handles the display and erasure of the prompt area, ensuring that the prompt remains visible when input is being handled.
  - It uses ANSI escape sequences to redraw the prompt block in place during typing.

- **Real-Time Output**:
  - All output from the chat loop (e.g., messages) is printed directly to the console, with the prompt area updated as needed.
  - This ensures that messages are displayed correctly even when other threads are active, such as rendering live regions or handling user input.

This implementation provides a robust solution for managing terminal I/O in a concurrent chat application, ensuring that messages are always displayed correctly and that the user interface remains responsive.
