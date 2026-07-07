"""write_project_documentation: incremental, model-written docs for the
project in the current working directory.

Every non-gitignored, non-configuration file is hashed into
.lodemaria/index.json (keyed by its path relative to the project root, so the
project can move or be cloned elsewhere without invalidating the docs). Files whose hash is new or changed
are fed to the coder model (config.DOC_MODEL), which writes markdown docs
mirroring the source tree under .lodemaria/docs/ — each doc streams live in
the terminal as it is written. Companion files sharing the
same path and stem (app.component.ts + app.component.html) are documented
together as one unit; stylesheets and markdown files are hashed but never
documented. Whenever
any doc changed, all per-file docs are fed to the general model
(config.DOC_SYNTH_MODEL) to produce .lodemaria/PROJECT.md, a comprehensive
overview of the whole project.
"""

import fnmatch
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

from lodemaria.config import (
    DOC_GROUP_MAX_CHARS,
    DOC_MODEL,
    DOC_PROJECT_MAX_CHARS,
    DOC_SYNTH_MODEL,
    OLLAMA_OPTIONS,
)
from lodemaria.llm import strip_think
from lodemaria.prompts import DOC_FILE_SYS, DOC_PROJECT_SYS
from lodemaria.streaming import stream_markdown
from lodemaria.terminal import console

LODEMARIA_DIR = ".lodemaria"
DOCS_DIRNAME = "docs"
INDEX_FILENAME = "index.json"
PROJECT_DOC_FILENAME = "PROJECT.md"

# Configuration/metadata files: neither hashed nor documented. Filenames that
# start with a dot (.gitignore, .env.local, ...) are treated as config too.
_CONFIG_EXTS = {
    ".json", ".json5", ".jsonc", ".yaml", ".yml", ".toml", ".xml", ".ini",
    ".cfg", ".conf", ".config", ".env", ".lock", ".properties", ".plist",
}

# Stylesheets and markdown (already documentation): hashed into the index,
# but never documented.
_NO_DOC_EXTS = {
    ".css", ".scss", ".sass", ".less", ".styl", ".pcss",
    ".md", ".mdx", ".markdown",
}

# Directories never scanned by the fallback walker (used when git is absent).
_FALLBACK_SKIP_DIRS = {
    ".git", LODEMARIA_DIR, "node_modules", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", "dist", "build", "target", ".pytest_cache",
}

_FENCE_RE = re.compile(r"^```[a-zA-Z-]*\s*\n(.*)\n```\s*$", re.DOTALL)


# ── File discovery ─────────────────────────────────────────────────────────────

def _git_files(root: Path) -> list[Path] | None:
    """Non-ignored files according to git itself (tracked + untracked that are
    not excluded). Returns None when git is unavailable or root is not a repo.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others",
             "--exclude-standard", "-z"],
            capture_output=True, check=True, timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return [root / p for p in out.decode("utf-8", "replace").split("\0") if p]


def _gitignore_patterns(root: Path) -> list[str]:
    """Patterns from the root .gitignore (negations skipped — approximation)."""
    path = root / ".gitignore"
    if not path.is_file():
        return []
    patterns = []
    for line in path.read_text("utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "!")):
            patterns.append(line.strip("/"))
    return patterns


def _fallback_files(root: Path) -> list[Path]:
    """Recursive walk honouring the root .gitignore via fnmatch. Only used when
    git cannot answer; close enough for the common patterns.
    """
    patterns = _gitignore_patterns(root)

    def ignored(rel: str, name: str) -> bool:
        return any(
            fnmatch.fnmatch(name, pat)
            or fnmatch.fnmatch(rel, pat)
            or fnmatch.fnmatch(rel, pat + "/*")
            for pat in patterns
        )

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        prefix = "" if rel_dir == "." else rel_dir + "/"
        dirnames[:] = [
            d for d in dirnames
            if d not in _FALLBACK_SKIP_DIRS and not ignored(prefix + d, d)
        ]
        for name in filenames:
            if not ignored(prefix + name, name):
                files.append(Path(dirpath) / name)
    return files


def _is_config(name: str) -> bool:
    return name.startswith(".") or PurePosixPath(name).suffix.lower() in _CONFIG_EXTS


def _hash_file(path: Path) -> str | None:
    """sha256 of the file content; None for binary or unreadable files."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return hashlib.sha256(data).hexdigest()


def _scan(root: Path) -> dict[str, str]:
    """Map relative posix path → sha256 for every file worth indexing."""
    listed = _git_files(root)
    if listed is None:
        listed = _fallback_files(root)
    index: dict[str, str] = {}
    for path in listed:
        if not path.is_file():  # git may list tracked files deleted from disk
            continue
        rel = path.relative_to(root).as_posix()
        if rel.split("/", 1)[0] in (".git", LODEMARIA_DIR):
            continue
        if _is_config(path.name):
            continue
        digest = _hash_file(path)
        if digest is not None:
            index[rel] = digest
    return index


# ── Index persistence (paths relative to the project root, posix-style) ───────

def _index_path(root: Path) -> Path:
    return root / LODEMARIA_DIR / INDEX_FILENAME


def _load_index(root: Path) -> dict[str, str]:
    try:
        raw = json.loads(_index_path(root).read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    index: dict[str, str] = {}
    for key, digest in raw.items():
        path = Path(key)
        if path.is_absolute():
            # Index written by an older version (absolute paths): migrate the
            # entry when it points inside this root, drop it otherwise.
            try:
                rel = path.resolve().relative_to(root).as_posix()
            except (ValueError, OSError):
                continue
        else:
            rel = path.as_posix()
        index[rel] = str(digest)
    return index


def _save_index(root: Path, index: dict[str, str]) -> None:
    payload = dict(sorted(index.items()))
    path = _index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), "utf-8")


# ── Grouping (companion files documented together) ─────────────────────────────

def _group_key(rel: str) -> str:
    """Path minus the final extension, so app.component.ts and
    app.component.html share the key "app.component"."""
    p = PurePosixPath(rel)
    return str(p.with_suffix("")) if p.suffix else rel


def _groups(index: dict[str, str]) -> dict[str, dict[str, str]]:
    """key → {relative path: hash} for documentable (non-stylesheet) files."""
    groups: dict[str, dict[str, str]] = {}
    for rel, digest in index.items():
        if PurePosixPath(rel).suffix.lower() not in _NO_DOC_EXTS:
            groups.setdefault(_group_key(rel), {})[rel] = digest
    return groups


def _doc_path(root: Path, key: str) -> Path:
    return root / LODEMARIA_DIR / DOCS_DIRNAME / (key + ".md")


# ── Model calls ────────────────────────────────────────────────────────────────

def _strip_fence(text: str) -> str:
    """Unwrap a response the model wrapped entirely in one ``` fence."""
    match = _FENCE_RE.match(text.strip())
    return match.group(1).strip() if match else text.strip()


def _ask_streaming(model: str, system: str, user: str, label: str, header: str) -> str:
    """One-shot doc-writing call, rendered live in the terminal as it streams."""
    raw = stream_markdown(
        label,
        header=header,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options=OLLAMA_OPTIONS,
    )
    return _strip_fence(strip_think(raw))


def _document_group(root: Path, key: str, members: dict[str, str]) -> str:
    sections = []
    for rel in sorted(members):
        try:
            text = (root / rel).read_text("utf-8", errors="replace")
        except OSError as e:
            text = f"(could not read this file: {e})"
        sections.append(f"=== File: {rel} ===\n{text}")
    source = "\n\n".join(sections)
    if len(source) > DOC_GROUP_MAX_CHARS:
        source = source[:DOC_GROUP_MAX_CHARS] + "\n…[content truncated]"
    return _ask_streaming(
        DOC_MODEL, DOC_FILE_SYS, source,
        f"Documentando {key}", f"[bold cyan]📄  {key}[/bold cyan]",
    )


def _write_project_doc(root: Path, groups: dict[str, dict[str, str]]) -> bool:
    """Feed every per-file doc to the model and save the general PROJECT.md."""
    parts = []
    for key in sorted(groups):
        try:
            parts.append(f"=== Docs for {key} ===\n{_doc_path(root, key).read_text('utf-8')}")
        except OSError:
            continue
    if not parts:
        return False
    material = "\n\n".join(parts)
    if len(material) > DOC_PROJECT_MAX_CHARS:
        material = material[:DOC_PROJECT_MAX_CHARS] + "\n…[content truncated]"
    overview = _ask_streaming(
        DOC_SYNTH_MODEL, DOC_PROJECT_SYS, material,
        "Documentação geral", f"[bold cyan]📖  {PROJECT_DOC_FILENAME}[/bold cyan]",
    )
    if not overview:
        return False
    (root / LODEMARIA_DIR / PROJECT_DOC_FILENAME).write_text(overview + "\n", "utf-8")
    return True


# ── Entry point ────────────────────────────────────────────────────────────────

def write_project_documentation() -> str:
    """Index the current folder and (re)write docs for new/changed files.
    Returns a summary string for the agent."""
    root = Path.cwd().resolve()
    console.print(f"[dim]Analisando arquivos em {root}[/dim]")

    index = _scan(root)
    if not index:
        return f"No documentable files found in {root}."

    old_index = _load_index(root)
    new_groups = _groups(index)
    old_groups = _groups(old_index)

    # Docs whose source group disappeared entirely → remove them.
    stale = [key for key in old_groups if key not in new_groups]
    for key in stale:
        _doc_path(root, key).unlink(missing_ok=True)
    _prune_empty_dirs(root / LODEMARIA_DIR / DOCS_DIRNAME)

    # A group is (re)documented when any member is new, changed, or removed,
    # or when its doc file is missing.
    todo = sorted(
        key for key, members in new_groups.items()
        if members != old_groups.get(key) or not _doc_path(root, key).is_file()
    )

    console.print(
        f"[dim]{len(index)} arquivo(s) indexado(s) · "
        f"{len(todo)} grupo(s) para documentar · "
        f"{len(stale)} doc(s) obsoleta(s) removida(s)[/dim]"
    )

    failed: list[str] = []
    for i, key in enumerate(todo, 1):
        console.print(f"[bold yellow]📚  ({i}/{len(todo)})[/bold yellow] [cyan]{key}[/cyan]")
        doc = _document_group(root, key, new_groups[key])
        if doc:
            path = _doc_path(root, key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(doc + "\n", "utf-8")
        else:
            failed.append(key)
            console.print(f"[red]O modelo não gerou documentação para '{key}'.[/red]")

    # Failed groups stay out of the index so the next run retries them.
    for key in failed:
        for rel in new_groups[key]:
            index.pop(rel, None)
    documented = [k for k in todo if k not in failed]

    project_doc = root / LODEMARIA_DIR / PROJECT_DOC_FILENAME
    regenerated = False
    if documented or stale or not project_doc.is_file():
        console.print("[bold yellow]📖  Gerando a documentação geral do projeto...[/bold yellow]")
        regenerated = _write_project_doc(root, new_groups)

    _save_index(root, index)

    lines = [
        f"Project documentation updated under {root / LODEMARIA_DIR}:",
        f"- {len(index)} file(s) hashed into {INDEX_FILENAME}",
        f"- {len(documented)} doc group(s) (re)written in {DOCS_DIRNAME}/",
        f"- {len(stale)} stale doc(s) removed",
        (f"- general documentation regenerated at {PROJECT_DOC_FILENAME}"
         if regenerated else "- general documentation unchanged"),
    ]
    if failed:
        lines.append(f"- FAILED groups (will be retried next run): {', '.join(failed)}")
    return "\n".join(lines)


def _prune_empty_dirs(docs_root: Path) -> None:
    """Best-effort removal of directories left empty by stale-doc deletion."""
    if not docs_root.is_dir():
        return
    for dirpath, _dirnames, _filenames in os.walk(docs_root, topdown=False):
        if Path(dirpath) != docs_root:
            try:
                os.rmdir(dirpath)  # only succeeds when empty
            except OSError:
                pass
