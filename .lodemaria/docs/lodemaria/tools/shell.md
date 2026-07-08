# Interactive Shell Sessions

This file provides a class and methods to manage interactive shell sessions within a chat application. Each session runs as an external process through the system shell, allowing real-time input and output from the command line. The `ShellSession` class encapsulates the process lifecycle and communicates with the chat through colored text in a bordered "box."

## Class Overview

### ShellSession
- **Properties**:
  - `id`: Unique identifier for each session.
  - `command`: Command to be executed by the shell.
  - `origin`: Whether the session was started by a user or an agent.
  - `returncode`: Exit code of the process.
  - `_lines`: List of lines from the process's standard output.
  - `_lock`: Lock for thread-safe access to the session's internal state.
  - `color`: Color cycle used to distinguish sessions.
  - `_pump`: Daemon thread that reads from the shell's stdout and prints it in a bordered box.

- **Methods**:
  - `__init__`: Initializes a new `ShellSession`.
  - `send(text: str) -> bool`: Writes one line to the process's stdin. Returns False if the write fails.
  - `output() -> str`: Returns the complete output of the session as a single string.
  - `terminate()`: Terminates the entire process tree, including the shell and its children.

### ShellManager
- **Properties**:
  - `_sessions`: Dictionary to store all active sessions.
  - `_next_id`: Next unique identifier for new sessions.
  - `_lock`: Lock for thread-safe access to the session list and completion queue.
  - `completions`: Queue of finished agent-started sessions.

- **Methods**:
  - `start(command: str, origin: str) -> ShellSession`: Starts a new shell session and returns it.
  - `_on_finish(session: ShellSession) -> None`: Handles the completion of an agent-started session by adding it to the completion queue and removing it from the active sessions dictionary.
  - `get(sid: int) -> ShellSession | None`: Retrieves a session by its ID.
  - `active_ids() -> list[int]`: Returns a list of IDs for all currently active sessions.
  - `terminate_all()`: Terminates all active sessions.

## Usage

To use this file in your application, you would typically:

1. **Import the necessary classes**:
   ```python
   from lodemaria.tools.shell import ShellSession, ShellManager
   ```

2. **Create an instance of `ShellManager`**:
   ```python
   shell_manager = ShellManager()
   ```

3. **Start a new session**:
   ```python
   session = shell_manager.start("ls -l", "user")
   ```

4. **Send input to the session**:
   ```python
   session.send("cat file.txt")
   ```

5. **Retrieve and handle completed sessions**:
   ```python
   while not shell_manager.completions.empty():
       session = shell_manager.completions.get()
       print(session.output())
   ```

6. **Terminate all active sessions**:
   ```python
   shell_manager.terminate_all()
   ```

This structure allows for efficient management of multiple interactive sessions and ensures that the chat environment remains clear and easy to follow.
