# Interactive shell sessions runnable from the chat, portable across OSes.

Each session wraps a subprocess started through the system shell (cmd.exe on Windows, /bin/sh on POSIX, selected automatically by ``shell=True``). Output is streamed live into the chat as a bordered "box" — a coloured gutter marks which session each line belongs to, so several sessions can run at once without their output becoming indistinguishable. The user can send lines to a session's stdin (line-based interactivity: REPLs and prompts work; full-screen curses apps do not).

Sessions are either user-started (``!<command>`` in the prompt) or agent-started
(the ``shell`` tool, after the user approves it). When an agent-started session
finishes it is pushed onto ``ShellManager.completions`` so the chat loop can feed
its output back to the model.

---

## Purpose and Role of The Project

The `lodemaria/tools/shell.py` module provides a straightforward way to run interactive shell sessions in a chat environment. It supports user-started commands (e.g., ``!command``) and agent-started sessions through the shell tool (`shell=True`). When an agent session finishes, it is pushed onto `ShellManager.completions`, allowing the chat loop to feed its output back.

---

## Class and Function Definitions

### ShellSession

- **Purpose**: A single running command. Spawns immediately; output pumps on a daemon thread.
- **Public Methods**:
  - `_pump`: Continuously reads from the process's stdout and outputs them into the chat.
  - `send(text): bool`: Writes one line to the process's stdin. Returns False if it can't be sent.
  - `output() -> str`: Returns the current output as a string.
  - `terminate() -> None`: Kills the whole process tree (shell + its children), cross-platform.

### ShellManager

- **Purpose**: Owns the live sessions and the queue of finished agent-started ones.
- **Public Methods**:
  - `start(command: str, origin: str) -> ShellSession`: Creates a new session.
  - `_on_finish(session: ShellSession) -> None`: Updates the list of completed sessions.
  - `get(sid: int) -> ShellSession | None`: Retrieves a session by ID.
  - `active_ids() -> list[int]`: Returns the IDs of all active sessions.
  - `terminate_all() -> None`: Terminates all running shell sessions.

---

## Example Usage

To start a new interactive shell session:

```python
session = lodemaria.tools.shell.start("!ping", "agent")
```

To send a line to a session's stdin (for REPLs and prompts):

```python
session.send("hello, world!")
```

To get the current output of a session:

```python
print(session.output())
```

---

## Note on Internal Logic

- **Internal Logic**: The shell processes each command as if it were part of an interactive application.
- **Algorithms and Side Effects**: The shell uses regular expressions to check for specific commands, which allows it to determine the nature of a session (user or agent), while still allowing concurrent executions without interleaving output.

---

## Cross-Platform Compatibility

The script is designed to run in both Windows and POSIX operating systems. It uses `subprocess.Popen` with `text=True`, so it can handle command line arguments properly. On Linux, it also uses the `shell=True` flag for shell execution.

---

## Running the Script

Ensure you have Python installed on your system to run this script. You can install it using pip:

```bash
pip install lodemaria-tools/shell.py
```

---

This documentation provides a comprehensive overview of the project, including its components and usage examples.
