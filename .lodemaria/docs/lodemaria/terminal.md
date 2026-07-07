## lodemaria/terminal.py

This file provides thread-safe terminal I/O functionality, portable across Windows and POSIX. It keeps a "Digite:" input prompt (plus an optional status line) pinned to the bottom of the screen while other threads print above it. A single lock guards both the input buffer and stdout writes so that concurrent prints erase the prompt block, print their content, then redraw it in place.

### Public Classes

#### PromptArea
Owns the bottom-of-screen input area (status line + prompt). All public methods are self-locking; `lock` is re-entrant so callers (e.g. SafeConsole) can hold it across an erase → print → redraw sequence.

**Methods:**
- **`__init__(self)`**: Initializes the `PromptArea` instance with an empty buffer, inactive status, and a lock.
- **`erase(self)`**: Erases the currently-drawn block (cursor ends where it started).
- **`draw(self)`**: Draws the block and remembers how many lines it occupies.
- **`set_status(self, text: str)`**: Updates the live status line above the prompt, redrawing in place.
- **`write(self, text: str)`**: Writes raw text to stdout, keeping the prompt at the bottom.
- **`hide(self)`**: Takes the prompt off the screen (e.g. while a live region renders). Typed characters keep accumulating unechoed until `show()` redraws them.
- **`show(self)`**: Restores the prompt hidden by `hide()`, including anything typed since.
- **`begin_input(self)`**: Begins input collection and draws the prompt.
- **`type_char(self, ch: str)`**: Types a character into the buffer and updates the screen.
- **`backspace(self)`**: Deletes the last character from the buffer and updates the screen.
- **`submit(self)`**: Closes the input area and returns the typed line (stripped).
- **`deactivate(self)`**: Deactivates the input area.

#### SafeConsole
Rich Console whose print() erases/restores the input prompt.

**Methods:**
- **`__init__(self, area: PromptArea, **kwargs)`**: Initializes the `SafeConsole` instance with the specified `PromptArea`.
- **`print(self, *args, **kwargs)`**: Overrides the base class method to erase and redraw the prompt during printing.

#### InputReader
Reads user input character-by-character on a background thread. Submitted lines are delivered through `lines`; `None` signals Ctrl+C/Ctrl+D.

**Methods:**
- **`__init__(self, area: PromptArea)`**: Initializes the `InputReader` instance with the specified `PromptArea`.
- **`start(self)`**: Starts the reader thread.
- **`allow(self)`**: Opens the prompt for the next line of input.
- **`_run(self)`**: Runs in a separate thread to read input characters and submit lines.
- **`_read_line(self)`**: Reads one line; returns `False` when the reader thread should stop.

### Shared Singletons

- **`prompt_area`**: A singleton instance of `PromptArea`.
- **`console`**: A singleton instance of `SafeConsole` using the shared `prompt_area`.
