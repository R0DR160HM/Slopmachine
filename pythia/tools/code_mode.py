"""Code Mode (--code) file tools: read_file, edit_file and create_file over
the project in the current working directory.

None of them exists until register_code_tools() runs — Code Mode calls it at
session start, so the regular chat mode never parses nor executes them.
read_file is stateless and runs in the shared tool registry. edit_file
(replace ONE exact snippet, shown to the user as before/after) and
create_file (a brand-new file) must be approved by the user, so the registry
only gets a fallback that refuses to run them outside the interactive
session; the real handling lives in ChatSession. All of them refuse paths
that escape the project root (the cwd), and read_file also refuses binary
files and truncates very large ones — edit_file applies against the full
on-disk content, so even files truncated on read are edited safely.
"""

import difflib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from pythia.config import CODE_FILE_MAX_CHARS
from pythia.llm import strip_think
from pythia.terminal import console
from pythia.tools.registry import register_tool


class CodeFileError(Exception):
    """A read/write the file tools must refuse (bad path, binary, missing)."""


# ── Fenced-block file edits ──────────────────────────────────────────────────
# Weaker models write code far more reliably inside ``` fences than escaped
# inside JSON. So in Code Mode, changing a file is expressed as fenced blocks
# whose info line is "<path>:before", "<path>:after" or "<path>:new" instead
# of an edit_file/create_file JSON call. A before/after pair replaces a
# snippet; a lone "<path>:new" block creates a whole file.

_FILE_BLOCK_RE = re.compile(r"```[ \t]*([^\n`]*?)[ \t]*\r?\n(.*?)```", re.DOTALL)
_BLOCK_KINDS = ("before", "after", "new")


def _strip_fence_body(body: str) -> str:
    """Drop the single trailing newline that separates a fenced block's
    content from its closing ``` (kept verbatim otherwise, so indentation
    survives)."""
    if body.endswith("\r\n"):
        return body[:-2]
    if body.endswith("\n"):
        return body[:-1]
    return body


def parse_block_edits(text: str) -> tuple[list[dict], list[str]]:
    """Scan an assistant turn for fenced file-edit blocks.

    Returns (calls, errors): `calls` are edit_file/create_file tool-call
    dicts — the same shape the JSON tools produced — ready for the normal
    approval flow; `errors` are feedback strings for malformed usage (a
    "before" with no matching "after", or vice-versa). Returns ([], []) when
    the turn contains no file-edit blocks at all."""
    calls: list[dict] = []
    errors: list[str] = []
    pending: dict[str, str] = {}  # path → its unmatched "before" content
    for info, body in _FILE_BLOCK_RE.findall(strip_think(text)):
        path, sep, kind = info.rpartition(":")
        if not sep or kind not in _BLOCK_KINDS or not path.strip():
            continue  # an ordinary code block, not a file edit
        path = path.strip()
        content = _strip_fence_body(body)
        if kind == "new":
            calls.append({"tool": "create_file", "path": path, "content": content})
        elif kind == "before":
            pending[path] = content
        else:  # after
            if path in pending:
                calls.append({
                    "tool": "edit_file", "path": path,
                    "before": pending.pop(path), "after": content,
                })
            else:
                errors.append(
                    f"a `{path}:after` block has no matching `{path}:before` "
                    "block before it — write the exact current snippet in a "
                    f"`{path}:before` block first, then its replacement in "
                    f"`{path}:after`."
                )
    for path in pending:
        errors.append(
            f"a `{path}:before` block has no matching `{path}:after` block — "
            "every `:before` needs an `:after` with the replacement snippet."
        )
    return calls, errors


def _resolve(path_str: str) -> tuple[Path, str]:
    """(absolute path, root-relative posix path) for a path inside the project
    root — the cwd. Raises CodeFileError for empty paths and paths that
    resolve outside the root (absolute paths, .., symlink escapes)."""
    cleaned = str(path_str).strip()
    if not cleaned:
        raise CodeFileError("the call had an empty 'path'")
    root = Path.cwd().resolve()
    try:
        path = (root / cleaned).resolve()
        rel = path.relative_to(root).as_posix()
    except (OSError, ValueError):
        raise CodeFileError(
            f"'{cleaned}' is outside the project root — only paths relative "
            f"to {root} are allowed"
        )
    return path, rel


def project_rel(path_str: str) -> str | None:
    """The root-relative form of a path the model passed, or None when it is
    invalid — lets the chat layer refer to the file by the same rel path the
    tool feedback messages use."""
    try:
        return _resolve(path_str)[1]
    except CodeFileError:
        return None


def read_project_file(path_str: str) -> tuple[str, str]:
    """(content, root-relative path) of one project text file. Raises
    CodeFileError when the path escapes the root, does not exist, is not a
    file, or is binary; content larger than CODE_FILE_MAX_CHARS is truncated
    with a visible marker."""
    path, rel = _resolve(path_str)
    if not path.is_file():
        raise CodeFileError(f"'{rel}' does not exist or is not a file")
    try:
        data = path.read_bytes()
    except OSError as e:
        raise CodeFileError(f"could not read '{rel}': {e}")
    if b"\0" in data[:8192]:
        raise CodeFileError(f"'{rel}' is a binary file")
    text = data.decode("utf-8", "replace")
    if len(text) > CODE_FILE_MAX_CHARS:
        text = text[:CODE_FILE_MAX_CHARS] + "\n…[content truncated]"
    return text, rel


@dataclass
class ChangePlan:
    """A validated edit_file/create_file call, ready to show and apply.

    For an edit, `before`/`after` are the snippet the user reviews and
    `new_text` is the full file content after the replacement. For a new
    file they are None and `new_text` is the whole content."""

    path: Path
    rel: str
    new_text: str
    before: str | None = None
    after: str | None = None
    at: int | None = None  # char offset of the replacement in new_text

    @property
    def is_new(self) -> bool:
        return self.before is None

    def apply(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.new_text, "utf-8")

    def applied_context(
        self, context_lines: int = 4, max_chars: int = 3000
    ) -> str | None:
        """The changed region of the new content with a few surrounding lines,
        fed back to the model so it sees the real result of its edit instead
        of relying on its memory of what it intended. None for new files."""
        if self.is_new or self.at is None or self.after is None:
            return None
        first = self.new_text[: self.at].count("\n")
        span = self.after.count("\n") + 1
        lines = self.new_text.splitlines()
        excerpt = "\n".join(
            lines[max(0, first - context_lines): first + span + context_lines]
        )
        if len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars] + "\n…[excerpt truncated]"
        return excerpt


def _read_full_text(path: Path, rel: str) -> str:
    """The file's complete text (no truncation — edits must never operate on
    a partial view). Raises CodeFileError for unreadable or binary files."""
    try:
        data = path.read_bytes()
    except OSError as e:
        raise CodeFileError(f"could not read '{rel}': {e}")
    if b"\0" in data[:8192]:
        raise CodeFileError(f"'{rel}' is a binary file")
    return data.decode("utf-8", "replace")


def _closest_snippet(text: str, before: str) -> str | None:
    """The stretch of the file most similar to a 'before' snippet that was
    not found (None when nothing comes close). Shown in the error so the
    model corrects itself from the file's real content instead of retrying
    its own remembered version."""
    if len(text) > 400_000:  # sliding windows over huge files cost too much
        return None
    target = before.strip("\n")
    lines = text.splitlines()
    if not lines or not target:
        return None
    span = target.count("\n") + 1
    windows = [
        "\n".join(lines[i:i + span])
        for i in range(max(1, len(lines) - span + 1))
    ]
    matches = difflib.get_close_matches(target, windows, n=1, cutoff=0.5)
    return matches[0] if matches else None


def prepare_edit(path_str: str, before: str, after: str) -> ChangePlan:
    """Validate an edit_file call — replace ONE exact occurrence of `before`
    with `after` — into a ChangePlan (nothing is written yet). Raises
    CodeFileError when the snippet is missing or ambiguous, so the model is
    told to copy it exactly or extend it until it is unique."""
    path, rel = _resolve(path_str)
    before, after = str(before), str(after)
    if not before:
        raise CodeFileError(
            "the 'before' snippet is empty — to create a new file use "
            "create_file instead"
        )
    if not path.is_file():
        raise CodeFileError(
            f"'{rel}' does not exist — use create_file to create it"
        )
    text = _read_full_text(path, rel)
    count = text.count(before)
    if count == 0:
        message = (
            f"the 'before' snippet was not found in '{rel}' — call read_file "
            "and copy the snippet EXACTLY as it appears, including whitespace "
            "and indentation"
        )
        hint = _closest_snippet(text, before)
        if hint:
            message += (
                f". The closest text currently in the file is:\n{hint}"
            )
        raise CodeFileError(message)
    if count > 1:
        raise CodeFileError(
            f"the 'before' snippet appears {count} times in '{rel}' — include "
            "more surrounding lines so it matches exactly one place"
        )
    return ChangePlan(
        path=path, rel=rel,
        new_text=text.replace(before, after, 1),
        before=before, after=after,
        at=text.index(before),
    )


def prepare_create(path_str: str, content: str) -> ChangePlan:
    """Validate a create_file call into a ChangePlan (nothing is written
    yet). Raises CodeFileError when the file already exists — changing an
    existing file must go through edit_file, snippet by snippet."""
    path, rel = _resolve(path_str)
    if path.exists():
        raise CodeFileError(
            f"'{rel}' already exists — use edit_file to change it"
        )
    content = str(content)
    if content and not content.endswith("\n"):
        content += "\n"
    return ChangePlan(path=path, rel=rel, new_text=content)


# ── Build-command detection (fed into the Code Mode system prompt) ────────────

def detect_build_commands() -> list[str]:
    """Build/test commands recognized from well-known files at the project
    root (the cwd). Best-effort — [] when nothing recognizable exists, in
    which case the agent is told to ask the user."""
    root = Path.cwd()
    found: list[str] = []

    pkg = root / "package.json"
    if pkg.is_file():
        try:
            scripts = json.loads(pkg.read_text("utf-8")).get("scripts", {})
        except (OSError, json.JSONDecodeError):
            scripts = {}
        for script in ("build", "test", "lint"):
            if script in scripts:
                found.append(f"npm run {script}")

    build_script = "build.ps1" if os.name == "nt" else "build.sh"
    if (root / build_script).is_file():
        found.append(
            f".\\{build_script}" if os.name == "nt" else f"./{build_script}"
        )

    if (root / "Makefile").is_file() or (root / "makefile").is_file():
        found.append("make")
    if (root / "Cargo.toml").is_file():
        found.extend(("cargo build", "cargo test"))
    if (root / "go.mod").is_file():
        found.extend(("go build ./...", "go test ./..."))
    if (root / "pom.xml").is_file():
        found.append("mvn package")
    if any((root / g).is_file() for g in ("build.gradle", "build.gradle.kts")):
        found.append("gradle build")

    return found


def build_info_line(commands: list[str]) -> str:
    """The system-prompt paragraph telling the agent how this project builds
    (or to ask the user when nothing was detected)."""
    if commands:
        listed = ", ".join(f'"{c}"' for c in commands)
        return (
            f"Build/test commands detected in this project: {listed}. "
            f'"{commands[0]}" runs AUTOMATICALLY after every applied change '
            "and you receive its result together with the change "
            "confirmation."
        )
    return (
        "No build/test command could be detected in this project. When you "
        "need to build or test, ASK the user which command to use — never "
        "guess one."
    )


# ── Registry wiring ────────────────────────────────────────────────────────────

def _run_read_file(call: dict, max_results: int) -> str:
    path_str = str(call.get("path", ""))
    console.print(f"\n[bold yellow]📂  Lendo arquivo:[/bold yellow] [cyan]{path_str}[/cyan]")
    try:
        text, rel = read_project_file(path_str)
    except CodeFileError as e:
        console.print(f"[red]{e}[/red]\n")
        return (
            f"read_file failed: {e}\n\n"
            "Fix the path (relative to the project root) and try again, or "
            "use project_search to locate the right file."
        )
    console.print(f"[dim]{len(text)} caractere(s) lidos de {rel}[/dim]\n")
    return (
        f"Current content of {rel}:\n\n{text}\n\n"
        "Now answer or make another tool call."
    )


def _run_interactive_only(call: dict, max_results: int) -> str:
    """edit_file, create_file and shell need the user's approval, which only
    the interactive chat can ask for. This fallback keeps any other caller
    from crashing on them."""
    return (
        f"The {call.get('tool')} tool is only available in the interactive "
        "Code Mode session and was not executed in this context."
    )


def register_code_tools() -> None:
    """Make read_file, edit_file, create_file and shell (Code Mode's
    friendlier name for shell_of_last_resort) parseable and executable.
    Called only when Code Mode starts, so the other modes never accept
    these calls."""
    register_tool("read_file", ("path",), _run_read_file)
    register_tool("edit_file", ("path", "before", "after"), _run_interactive_only)
    register_tool("create_file", ("path", "content"), _run_interactive_only)
    register_tool("shell", ("command",), _run_interactive_only)
