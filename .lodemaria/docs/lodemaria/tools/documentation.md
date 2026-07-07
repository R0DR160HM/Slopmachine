# Documentation Generation Tool (documentation.py)

This module is responsible for generating incremental project documentation using a language model. It hashes all non-gitignored, non-configuration files into a JSON index file and feeds changed or new files to the language model to produce markdown documentation. Companion files sharing the same path and stem are documented together as one unit.

## Public Functions

### `write_project_documentation() -> str`

**Purpose:** Indexes the current folder and (re)writes docs for new/changed files.

**Behavior:**
- Analyzes files in the current working directory.
- Hashes all non-gitignored, non-configuration files into `.lodemaria/index.json`.
- Feeds changed or new files to a language model to produce markdown documentation.
- Documents companion files sharing the same path and stem as one unit.
- Generates a comprehensive project overview document.

**Returns:**
- A summary string indicating the number of files indexed, groups documented, stale docs removed, and whether the project overview was regenerated.

**Side Effects:**
- Writes markdown documentation to `.lodemaria/docs/` directory.
- Writes a general project overview document to `.lodemaria/PROJECT.md`.
- Prunes empty directories in `.lodemaria/docs/`.

## Internal Functions

### `_git_files(root: Path) -> list[Path] | None`

**Purpose:** Retrieves non-ignored files according to git itself.

**Parameters:**
- `root`: The root directory of the project.

**Returns:**
- A list of paths to non-ignored files, or `None` if git is unavailable or the root is not a repository.

### `_gitignore_patterns(root: Path) -> list[str]`

**Purpose:** Retrieves patterns from the root `.gitignore`.

**Parameters:**
- `root`: The root directory of the project.

**Returns:**
- A list of gitignore patterns.

### `_fallback_files(root: Path) -> list[Path]`

**Purpose:** Performs a fallback file discovery using `os.walk()` and the root `.gitignore`.

**Parameters:**
- `root`: The root directory of the project.

**Returns:**
- A list of paths to non-ignored files.

### `_is_config(name: str) -> bool`

**Purpose:** Determines if a file name is considered a configuration file.

**Parameters:**
- `name`: The file name.

**Returns:**
- `True` if the file name is a configuration file, otherwise `False`.

### `_hash_file(path: Path) -> str | None`

**Purpose:** Computes the SHA256 hash of a file's content.

**Parameters:**
- `path`: The path to the file.

**Returns:**
- The SHA256 hash of the file's content, or `None` if the file is binary or unreadable.

### `_scan(root: Path) -> dict[str, str]`

**Purpose:** Scans the project root and returns a dictionary mapping relative POSIX paths to SHA256 hashes of documentable files.

**Parameters:**
- `root`: The root directory of the project.

**Returns:**
- A dictionary mapping relative POSIX paths to file hashes.

### `_index_path(root: Path) -> Path`

**Purpose:** Generates the path for the index file.

**Parameters:**
- `root`: The root directory of the project.

**Returns:**
- The path to the `.lodemaria/index.json` file.

### `_load_index(root: Path) -> dict[str, str]`

**Purpose:** Loads the index from the JSON file.

**Parameters:**
- `root`: The root directory of the project.

**Returns:**
- A dictionary mapping relative POSIX paths to file hashes, loaded from the `.lodemaria/index.json` file.

### `_save_index(root: Path, index: dict[str, str]) -> None`

**Purpose:** Saves the index to the JSON file.

**Parameters:**
- `root`: The root directory of the project.
- `index`: A dictionary mapping relative POSIX paths to file hashes.

### `_group_key(rel: str) -> str`

**Purpose:** Generates a group key for companion files sharing the same path and stem.

**Parameters:**
- `rel`: The relative path of the file.

**Returns:**
- A string representing the group key.

### `_groups(index: dict[str, str]) -> dict[str, dict[str, str]]`

**Purpose:** Groups documentable files by their common prefix (excluding extensions).

**Parameters:**
- `index`: A dictionary mapping relative POSIX paths to file hashes.

**Returns:**
- A dictionary where keys are group keys and values are dictionaries mapping relative POSIX paths to file hashes.

### `_doc_path(root: Path, key: str) -> Path`

**Purpose:** Generates the path for a document file.

**Parameters:**
- `root`: The root directory of the project.
- `key`: The group key.

**Returns:**
- The path to the document file in `.lodemaria/docs/`.

### `_strip_fence(text: str) -> str`

**Purpose:** Strips any Markdown fences from a text string.

**Parameters:**
- `text`: The input text.

**Returns:**
- The input text with any Markdown fences stripped.

### `_ask_streaming(model: str, system: str, user: str, label: str, header: str) -> str`

**Purpose:** Sends a request to the language model and streams the response in real-time.

**Parameters:**
- `model`: The language model to use.
- `system`: System instructions for the model.
- `user`: User input for the model.
- `label`: Label for the streaming output.
- `header`: Header for the streaming output.

**Returns:**
- The generated Markdown document.

### `_document_group(root: Path, key: str, members: dict[str, str]) -> str`

**Purpose:** Documents a group of companion files.

**Parameters:**
- `root`: The root directory of the project.
- `key`: The group key.
- `members`: A dictionary mapping relative POSIX paths to file hashes.

**Returns:**
- The generated Markdown document for the group.

### `_write_project_doc(root: Path, groups: dict[str, dict[str, str]]) -> bool`

**Purpose:** Writes a general project overview document using the language model.

**Parameters:**
- `root`: The root directory of the project.
- `groups`: A dictionary where keys are group keys and values are dictionaries mapping relative POSIX paths to file hashes.

**Returns:**
- `True` if the project overview was successfully written, otherwise `False`.

### `_prune_empty_dirs(docs_root: Path) -> None`

**Purpose:** Prunes empty directories in `.lodemaria/docs/`.

**Parameters:**
- `docs_root`: The root directory for the documentation files.

This module is crucial for keeping the project documentation up-to-date automatically and efficiently, leveraging language models to handle text generation.
