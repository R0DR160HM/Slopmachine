"""write_project_documentation: incremental, model-written docs for the
project in the current working directory.

Every non-gitignored, non-configuration file — dotfiles and files inside
dotfolders (.github/, .vscode/, ...) are always ignored — is hashed into
.pythia/index.json (keyed by its path relative to the project root, so the
project can move or be cloned elsewhere without invalidating the docs). Files whose hash is new or changed
are fed to the default model (config.DEFAULT_MODEL), which writes markdown docs
mirroring the source tree under .pythia/docs/ — each doc streams live in
the terminal as it is written. Companion files sharing the
same path and stem (app.component.ts + app.component.html) are documented
together as one unit; stylesheets and markdown files are hashed but never
documented. Each group's markdown doc mirrors its source path: group
"pythia/llm" is documented at ".pythia/docs/pythia/llm.md".

Diagrams are NOT generated here: they are drawn on demand in the chat —
show_answer_diagrams renders any PlantUML an assistant answer writes inline
(or any .puml file it mentions) as ASCII art with the vendored PlantUML jar
(vendor/plantuml, bundled into frozen builds; needs java on PATH). Docs and
diagrams saved by older layouts (one folder per group, or "-meta" folders)
are adopted or cleaned up on the next run.

The group's source files and markdown doc are also
embedded with config.EMBED_MODEL (sliced to fit its 2k-token context)
directly into .pythia/embeddings.json — the semantic index consumed by the
project_search tool. Like index.json it is maintained incrementally: the
index is rewritten after every group, and records belonging to groups that
disappeared or changed are dropped/replaced.
"""

import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

from rich.text import Text

from pythia import config
from pythia.config import (
    CODE_OLLAMA_OPTIONS,
    DOC_GROUP_MAX_CHARS,
    EMBED_SLICE_CHARS,
    EMBED_SLICE_OVERLAP,
)
from pythia.llm import embed_documents, strip_think
from pythia.prompts import DOC_FILE_SYS
from pythia.streaming import stream_markdown
from pythia.terminal import console

PYTHIA_DIR = ".pythia"
DOCS_DIRNAME = "docs"
INDEX_FILENAME = "index.json"

# Suffix of the folders the old layout used ("<name>-meta/", beside a
# "<name>.md" doc) — kept only so upgraded projects get their leftovers
# cleaned up.
META_SUFFIX = "-meta"
# Diagram types older versions generated during documentation — kept only so
# their leftover "<type>-*.puml/.svg" files are still cleaned up.
DIAGRAM_TYPES = ("sequence", "class", "deployment", "regex")

# The project-wide semantic index, directly under .pythia/.
EMBED_FILENAME = "embeddings.json"

# Where the PlantUML jar lives, relative to the project source root — frozen
# builds carry this folder inside the executable (see build.sh / build.ps1).
PLANTUML_VENDOR_DIR = "vendor/plantuml"
PLANTUML_TIMEOUT = 120  # seconds per rendered diagram

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
# Dot-directories need no listing here — the walker prunes them all.
_FALLBACK_SKIP_DIRS = {
    "node_modules", "__pycache__", "venv", "dist", "build", "target",
    "vendor",
}

_FENCE_RE = re.compile(r"^```[a-zA-Z-]*\s*\n(.*)\n```\s*$", re.DOTALL)

# Test files are never indexed nor documented: anything inside a test/tests
# or mock/mocks folder, or named like foo.test.ts / foo_test.go / foo.spec.ts
# / test_foo.py.
_TEST_DIR_RE = re.compile(r"^(tests?|mocks?)$", re.IGNORECASE)
_TEST_NAME_RE = re.compile(r"(^|[._])(test|spec)(?=[._])", re.IGNORECASE)


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
            if not d.startswith(".")
            and d not in _FALLBACK_SKIP_DIRS
            and not ignored(prefix + d, d)
        ]
        for name in filenames:
            if not ignored(prefix + name, name):
                files.append(Path(dirpath) / name)
    return files


def _is_config(name: str) -> bool:
    """Configuration/metadata files, plus extensionless ones (Dockerfile,
    LICENSE, Makefile, ...): never indexed nor documented."""
    suffix = PurePosixPath(name).suffix.lower()
    return name.startswith(".") or not suffix or suffix in _CONFIG_EXTS


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
        parts = rel.split("/")
        # Dotfiles and anything under a dotfolder (.git, .pythia, .github,
        # ...) are never indexed — that also covers everything this tool
        # generates, since it all lives under .pythia/.
        if any(part.startswith(".") for part in parts):
            continue
        if (any(_TEST_DIR_RE.match(part) for part in parts[:-1])
                or _TEST_NAME_RE.search(path.name)):
            continue
        if _is_config(path.name):
            continue
        digest = _hash_file(path)
        if digest is not None:
            index[rel] = digest
    return index


# ── Index persistence (paths relative to the project root, posix-style) ───────

def _index_path(root: Path) -> Path:
    return root / PYTHIA_DIR / INDEX_FILENAME


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


def _documentable(rel: str) -> bool:
    return PurePosixPath(rel).suffix.lower() not in _NO_DOC_EXTS


def _groups(index: dict[str, str]) -> dict[str, dict[str, str]]:
    """key → {relative path: hash} for documentable files."""
    groups: dict[str, dict[str, str]] = {}
    for rel, digest in index.items():
        if _documentable(rel):
            groups.setdefault(_group_key(rel), {})[rel] = digest
    return groups


def _doc_path(root: Path, key: str) -> Path:
    """The group's markdown doc, mirroring its source path under .pythia/docs/
    — e.g. ".pythia/docs/pythia/llm.md" for group "pythia/llm"."""
    return root / PYTHIA_DIR / DOCS_DIRNAME / (key + ".md")


# ── Model calls ────────────────────────────────────────────────────────────────

def _strip_fence(text: str) -> str:
    """Unwrap a response the model wrapped entirely in one ``` fence."""
    match = _FENCE_RE.match(text.strip())
    return match.group(1).strip() if match else text.strip()


def _ask_streaming(model: str, system: str, user: str, label: str, header: str) -> str:
    """One-shot doc-writing call, rendered live in the terminal as it streams.
    Uses the near-greedy Code Mode options: docs must describe the source,
    not improvise around it."""
    raw = stream_markdown(
        label,
        header=header,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options=CODE_OLLAMA_OPTIONS,
    )
    return _strip_fence(strip_think(raw))


def _group_source(root: Path, members: dict[str, str]) -> str:
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
    return source


def _document_group(key: str, source: str) -> str:
    return _ask_streaming(
        config.DEFAULT_MODEL, DOC_FILE_SYS, source,
        f"Documentando {key}", f"[bold cyan]📄  {key}[/bold cyan]",
    )


# ── Cleanup of generated outputs (incl. diagrams from older versions) ─────────

def _clear_diagrams(dir_path: Path) -> None:
    """Remove diagrams generated by older versions — only "<type>-*.puml/.svg",
    so the markdown doc and anything the user placed in the folder are kept."""
    if not dir_path.is_dir():
        return
    for dtype in DIAGRAM_TYPES:
        for ext in (".puml", ".svg"):
            for stale in dir_path.glob(f"{dtype}-*{ext}"):
                stale.unlink(missing_ok=True)


def _clear_old_layouts(root: Path, key: str) -> None:
    """Outputs from older layouts: the group's own folder ("docs/<key>/"
    holding the doc and diagrams) and the "docs/<key>-meta/" folder the oldest
    layout kept beside the doc. Each folder is removed only when nothing else
    (user-placed files, other groups' folders) remains in it."""
    docs_root = root / PYTHIA_DIR / DOCS_DIRNAME
    group_dir = docs_root / key
    (group_dir / (PurePosixPath(key).name + ".md")).unlink(missing_ok=True)
    _clear_diagrams(group_dir)
    try:
        group_dir.rmdir()  # only succeeds when empty
    except OSError:
        pass
    meta_dir = docs_root / (key + META_SUFFIX)
    if not meta_dir.is_dir():
        return
    _clear_diagrams(meta_dir)
    (meta_dir / EMBED_FILENAME).unlink(missing_ok=True)
    try:
        meta_dir.rmdir()  # only succeeds when empty
    except OSError:
        pass


def _migrate_group_doc(root: Path, key: str) -> None:
    """Adopt a doc written by the previous layout ("docs/<key>/<stem>.md",
    inside the group's own folder) as today's "docs/<key>.md" when the latter
    is missing, then drop the older layouts' leftovers — an upgraded project
    keeps its docs instead of re-documenting every group."""
    old_doc = (root / PYTHIA_DIR / DOCS_DIRNAME / key
               / (PurePosixPath(key).name + ".md"))
    new_doc = _doc_path(root, key)
    if old_doc.is_file() and not new_doc.is_file():
        try:
            old_doc.replace(new_doc)
        except OSError:
            pass
    _clear_old_layouts(root, key)


def _remove_group_output(root: Path, key: str) -> None:
    """Delete the group's generated doc and any older-layout outputs."""
    _doc_path(root, key).unlink(missing_ok=True)
    _clear_old_layouts(root, key)


# ── PlantUML rendering for chat answers (vendored jar, java required) ──────────

_PLANTUML_BLOCK_RE = re.compile(r"@start\w+.*?@end\w+", re.DOTALL)


def _plantuml_jar() -> Path | None:
    """The vendored PlantUML jar: inside the frozen executable's extracted
    data (PyInstaller) or under vendor/ at the source checkout root."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "."))
    else:
        base = Path(__file__).resolve().parents[2]
    return next(iter(sorted((base / PLANTUML_VENDOR_DIR).glob("*.jar"))), None)


def _plantuml_cmd(jar: Path) -> list[str] | None:
    """Base command line to run the jar; None when java is not on PATH."""
    java = shutil.which("java")
    if java is None:
        return None
    cmd = [java, "-Djava.awt.headless=true", "-jar", str(jar),
           "-charset", "UTF-8"]
    if shutil.which("dot") is None:
        # Graphviz is absent: fall back to PlantUML's pure-java layout engine
        # so class/deployment diagrams still render.
        cmd.append("-Playout=smetana")
    return cmd


def _render_txt(jar: Path, puml: str) -> str:
    """ASCII-art rendering of one diagram, shown in the chat (never saved).
    Empty when java is missing or PlantUML cannot render this diagram."""
    cmd = _plantuml_cmd(jar)
    if cmd is None:
        return ""
    try:
        proc = subprocess.run(
            cmd + ["-ttxt", "-pipe"], input=puml.encode("utf-8"),
            capture_output=True, timeout=PLANTUML_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.decode("utf-8", "replace").rstrip()


# Candidate ".puml" mentions inside an assistant answer (path or bare name).
_PUML_MENTION_RE = re.compile(r"[^\s`'\"()\[\]]+\.puml")


def show_answer_diagrams(text: str) -> None:
    """Render the diagrams an assistant answer carries as ASCII art in the
    chat: every mentioned .puml file found under .pythia/, plus any PlantUML
    block (@start...@end) written directly in the answer. Anything that
    cannot be found or rendered is silently skipped."""
    jar = _plantuml_jar()
    if jar is None:
        return
    rendered: set[str] = set()

    def show(puml: str, header: str | None = None) -> None:
        txt = _render_txt(jar, puml)
        if txt and txt not in rendered:
            rendered.add(txt)
            if header:
                console.print(f"[bold cyan]🧩  {header}[/bold cyan]")
            console.print(Text(txt))

    docs_root = Path.cwd() / PYTHIA_DIR
    if docs_root.is_dir():
        seen: set[Path] = set()
        for mention in _PUML_MENTION_RE.findall(text):
            name = PurePosixPath(mention.replace("\\", "/")).name
            try:
                matches = sorted(p for p in docs_root.rglob(name) if p.is_file())
            except OSError:
                continue
            for path in matches:
                if path in seen:
                    continue
                seen.add(path)
                try:
                    show(path.read_text("utf-8"), header=name)
                except OSError:
                    continue

    # PlantUML the answer wrote inline is rendered the same way.
    for block in _PLANTUML_BLOCK_RE.findall(text):
        show(block)


# ── Embeddings (the semantic index behind the project_search tool) ─────────────

_embed_warned = False


def _slices(text: str) -> list[str]:
    """Overlapping chunks sized for the embedding model's 2k-token context."""
    text = text.strip()
    if not text:
        return []
    step = EMBED_SLICE_CHARS - EMBED_SLICE_OVERLAP
    chunks = []
    for start in range(0, len(text), step):
        chunks.append(text[start:start + EMBED_SLICE_CHARS])
        if start + EMBED_SLICE_CHARS >= len(text):
            break
    return chunks


def _embed_path(root: Path) -> Path:
    return root / PYTHIA_DIR / EMBED_FILENAME


def _load_embeddings(root: Path) -> list[dict]:
    """Records from .pythia/embeddings.json; empty when the index is missing,
    unreadable, or was built with a different embedding model (which makes
    every group re-embed, since none appears indexed anymore)."""
    try:
        data = json.loads(_embed_path(root).read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if data.get("model") != config.EMBED_MODEL:
        return []
    records = data.get("records", [])
    return records if isinstance(records, list) else []


def _save_embeddings(root: Path, records: list[dict]) -> None:
    path = _embed_path(root)
    if not records:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"model": config.EMBED_MODEL, "records": records},
                   ensure_ascii=False),
        "utf-8",
    )


def _embed_group(
    root: Path, key: str, members: dict[str, str], doc: str
) -> list[dict]:
    """Embed the group's source files and markdown doc.
    Returns the records (tagged with the group key) ready to be merged into
    .pythia/embeddings.json; on failure (e.g. the embedding model is missing)
    warns once and returns []."""
    global _embed_warned
    entries: list[dict] = []

    def add(origin: str, kind: str, text: str) -> None:
        for i, chunk in enumerate(_slices(text)):
            entries.append(
                {"group": key, "origin": origin, "kind": kind,
                 "slice": i, "text": chunk}
            )

    for rel in sorted(members):
        try:
            add(rel, "source", (root / rel).read_text("utf-8", errors="replace"))
        except OSError:
            continue
    add(key + ".md", "doc", doc)
    if not entries:
        return []

    console.print(f"[dim]🧠  Gerando {len(entries)} embedding(s)...[/dim]")
    try:
        vectors = embed_documents([e["text"] for e in entries])
    except Exception as e:
        if not _embed_warned:
            _embed_warned = True
            console.print(
                f"[yellow]⚠  Não consegui gerar embeddings ({e}) — confira se "
                f"o modelo '{config.EMBED_MODEL}' está disponível no Ollama. "
                f"A busca na documentação não será atualizada.[/yellow]"
            )
        return []
    for entry, vector in zip(entries, vectors):
        entry["vector"] = vector
    return entries


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

    # Docs whose source group disappeared entirely → remove them (and any
    # old-layout leftovers). Surviving groups get older-layout docs adopted
    # into today's layout up front, so a layout upgrade never forces a full
    # re-documentation.
    stale = [key for key in old_groups if key not in new_groups]
    for key in stale:
        _remove_group_output(root, key)
    for key in new_groups:
        _migrate_group_doc(root, key)
    _prune_empty_dirs(root / PYTHIA_DIR / DOCS_DIRNAME)

    # The search index is pruned the same way: records of groups that no
    # longer exist are dropped immediately, before any model call runs.
    embeddings = _load_embeddings(root)
    pruned = [r for r in embeddings if r.get("group") in new_groups]
    if len(pruned) != len(embeddings):
        embeddings = pruned
        _save_embeddings(root, embeddings)
    embedded_groups = {r.get("group") for r in embeddings}

    # A group is (re)documented when any member is new, changed, or removed,
    # or when its doc file or search-index records are missing.
    todo = sorted(
        key for key, members in new_groups.items()
        if members != old_groups.get(key)
        or not _doc_path(root, key).is_file()
        or key not in embedded_groups
    )

    console.print(
        f"[dim]{len(index)} arquivo(s) indexado(s) · "
        f"{len(todo)} grupo(s) para documentar · "
        f"{len(stale)} doc(s) obsoleta(s) removida(s)[/dim]"
    )

    # The index is persisted incrementally — an entry is updated the moment
    # its doc is written — so an interrupted run resumes where it stopped
    # instead of re-documenting everything. Start from the old index minus
    # deleted files, with undocumented files (stylesheets, markdown) already
    # refreshed since no doc depends on them.
    persisted = {rel: digest for rel, digest in old_index.items() if rel in index}
    for rel, digest in index.items():
        if not _documentable(rel):
            persisted[rel] = digest
    _save_index(root, persisted)

    failed: list[str] = []
    slices_embedded = 0
    for i, key in enumerate(todo, 1):
        console.print(f"[bold yellow]📚  ({i}/{len(todo)})[/bold yellow] [cyan]{key}[/cyan]")
        source = _group_source(root, new_groups[key])
        doc = _document_group(key, source)
        if doc:
            path = _doc_path(root, key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(doc + "\n", "utf-8")
            # The group's records are replaced in the search index right away
            # — like index.json, it is rewritten after every group. When
            # embedding fails the old records are dropped anyway (they
            # describe the previous source) and the group retries next run.
            records = _embed_group(root, key, new_groups[key], doc)
            embeddings = [r for r in embeddings if r.get("group") != key]
            embeddings.extend(records)
            _save_embeddings(root, embeddings)
            slices_embedded += len(records)
            persisted.update(new_groups[key])
        else:
            failed.append(key)
            # Failed groups stay out of the index so the next run retries them.
            for rel in new_groups[key]:
                persisted.pop(rel, None)
            console.print(f"[red]O modelo não gerou documentação para '{key}'.[/red]")
        _save_index(root, persisted)
    documented = [k for k in todo if k not in failed]

    lines = [
        f"Project documentation updated under {root / PYTHIA_DIR}:",
        f"- {len(persisted)} file(s) hashed into {INDEX_FILENAME}",
        f"- {len(documented)} doc group(s) (re)written in {DOCS_DIRNAME}/ "
        f"(mirroring the source tree)",
        f"- {slices_embedded} text slice(s) embedded for semantic search",
        f"- {len(stale)} stale doc(s) removed",
        f"- search index at {EMBED_FILENAME}: {len(embeddings)} slice(s) total",
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
