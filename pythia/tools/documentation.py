"""write_project_documentation: incremental, model-written docs for the
project in the current working directory.

Every non-gitignored, non-configuration file — dotfiles and files inside
dotfolders (.github/, .vscode/, ...) are always ignored — is hashed into
.pythia/index.json (keyed by its path relative to the project root, so the
project can move or be cloned elsewhere without invalidating the docs). Files whose hash is new or changed
are fed to the coder model (config.DOC_MODEL), which writes markdown docs
mirroring the source tree under .pythia/docs/ — each doc streams live in
the terminal as it is written. Companion files sharing the
same path and stem (app.component.ts + app.component.html) are documented
together as one unit; stylesheets and markdown files are hashed but never
documented. After each doc is written the model is asked which UML diagrams
apply (sequence, class, deployment, PlantUML regex — multiple of each type
allowed) and then generates each
one as PlantUML, one model call per diagram, saved in a "<name>-meta"
folder beside the group's markdown doc under .pythia/docs/. Each diagram
is rendered with the
vendored PlantUML jar (vendor/plantuml, bundled into frozen builds): an
ASCII version is shown in the chat as it is created (never saved) and an
.svg image is saved beside its .puml. Rendering needs java on PATH and is
skipped with a warning when it is missing.

The group's source files, markdown doc and PlantUML diagrams are also
embedded with config.EMBED_MODEL (sliced to fit its 2k-token context) into
"<name>-meta/embeddings.json"; whenever anything changed, all per-group
embeddings are composed into .pythia/embeddings.json — the semantic index
consumed by the project_search tool.
Whenever
any doc changed, all per-file docs are fed to the general model
(config.DOC_SYNTH_MODEL) to produce .pythia/PROJECT.md, a comprehensive
overview of the whole project.
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
    DOC_DIAGRAM_DOC_MAX_CHARS,
    DOC_DIAGRAMS_MAX,
    DOC_GROUP_MAX_CHARS,
    DOC_PROJECT_MAX_CHARS,
    EMBED_SLICE_CHARS,
    EMBED_SLICE_OVERLAP,
    OLLAMA_OPTIONS,
)
from pythia.llm import ask, embed_documents, strip_think
from pythia.prompts import (
    DOC_DIAGRAM_GEN_SYS,
    DOC_DIAGRAM_SELECT_SYS,
    DOC_FILE_SYS,
    DOC_PROJECT_SYS,
)
from pythia.streaming import stream_markdown
from pythia.terminal import console

PYTHIA_DIR = ".pythia"
DOCS_DIRNAME = "docs"
INDEX_FILENAME = "index.json"
PROJECT_DOC_FILENAME = "PROJECT.md"

# Generated diagrams and embeddings for group "pythia/llm" live in
# ".pythia/docs/pythia/llm-meta/", right next to the group's markdown doc.
META_SUFFIX = "-meta"
DIAGRAM_TYPES = ("sequence", "class", "deployment", "regex")

# Per-group embeddings file inside "<name>-meta/"; the composed, project-wide
# index shares the name and lives directly under .pythia/.
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
# folder, or named like foo.test.ts / foo_test.go / foo.spec.ts / test_foo.py.
_TEST_DIR_RE = re.compile(r"^tests?$", re.IGNORECASE)
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
    return root / PYTHIA_DIR / DOCS_DIRNAME / (key + ".md")


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
        config.DOC_MODEL, DOC_FILE_SYS, source,
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
        config.DOC_SYNTH_MODEL, DOC_PROJECT_SYS, material,
        "Documentação geral", f"[bold cyan]📖  {PROJECT_DOC_FILENAME}[/bold cyan]",
    )
    if not overview:
        return False
    (root / PYTHIA_DIR / PROJECT_DOC_FILENAME).write_text(overview + "\n", "utf-8")
    return True


# ── PlantUML diagrams (saved beside the documented source files) ──────────────

_PLANTUML_BLOCK_RE = re.compile(r"@start\w+.*?@end\w+", re.DOTALL)


def _meta_dir(root: Path, key: str) -> Path:
    return root / PYTHIA_DIR / DOCS_DIRNAME / (key + META_SUFFIX)


def _clear_meta(dir_path: Path) -> None:
    """Remove previously generated meta files — only "<type>-*.puml/.svg" and
    the embeddings file, so anything the user placed in the folder is
    preserved — then the folder itself when empty."""
    if not dir_path.is_dir():
        return
    for dtype in DIAGRAM_TYPES:
        for ext in (".puml", ".svg"):
            for stale in dir_path.glob(f"{dtype}-*{ext}"):
                stale.unlink(missing_ok=True)
    (dir_path / EMBED_FILENAME).unlink(missing_ok=True)
    try:
        dir_path.rmdir()  # only succeeds when empty
    except OSError:
        pass


def _parse_diagram_specs(text: str) -> list[dict[str, str]]:
    """Diagram specs from the selection reply: a JSON array of objects with
    "type" (+ optional "title"/"instructions"); bare type strings tolerated."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    if not isinstance(items, list):
        return []
    specs: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            item = {"type": item}
        if not isinstance(item, dict):
            continue
        raw_type = str(item.get("type", "")).strip().lower()
        dtype = next((t for t in DIAGRAM_TYPES if t in raw_type), None)
        if dtype is None:
            continue
        specs.append({
            "type": dtype,
            "title": str(item.get("title", "")).strip(),
            "instructions": str(
                item.get("instructions", item.get("description", ""))
            ).strip(),
        })
    return specs[:DOC_DIAGRAMS_MAX]


def _select_diagrams(source: str, doc: str) -> list[dict[str, str]]:
    """Ask the model which UML diagrams (if any) apply to this group."""
    doc_part = doc[:DOC_DIAGRAM_DOC_MAX_CHARS]
    reply = ask(
        config.DOC_MODEL, DOC_DIAGRAM_SELECT_SYS,
        f"{source}\n\n=== Documentation just written ===\n{doc_part}",
        "Avaliando diagramas",
    )
    return _parse_diagram_specs(reply)


def _normalize_plantuml(text: str, dtype: str) -> str:
    """The @start…@end block of the reply; bare content gets wrapped. Text the
    model echoes after the @start tag (e.g. the diagram spec) is dropped."""
    text = text.strip()
    if not text:
        return ""
    match = _PLANTUML_BLOCK_RE.search(text)
    if match:
        block = match.group().strip()
        return re.sub(r"^(@start\w+)[^\n]*", r"\1", block)
    start, end = (
        ("@startregex", "@endregex") if dtype == "regex"
        else ("@startuml", "@enduml")
    )
    return f"{start}\n{text}\n{end}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


# ── PlantUML rendering (vendored jar, java required) ───────────────────────────

_plantuml_warned = False


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


def _render_svgs(jar: Path | None, pumls: list[Path]) -> int:
    """Render .puml files to .svg images saved in the same folder. Returns how
    many were rendered; warns once per run when java or the jar is missing."""
    global _plantuml_warned
    if not pumls:
        return 0
    cmd = _plantuml_cmd(jar) if jar is not None else None
    if cmd is None:
        if not _plantuml_warned:
            _plantuml_warned = True
            missing = ("java" if jar is not None
                       else f"o PlantUML ({PLANTUML_VENDOR_DIR}/*.jar)")
            console.print(
                f"[yellow]⚠  {missing} não foi encontrado — os .puml foram "
                f"salvos, mas as imagens .svg não serão geradas.[/yellow]"
            )
        return 0
    try:
        proc = subprocess.run(
            cmd + ["-tsvg"] + [str(p) for p in pumls],
            capture_output=True, timeout=PLANTUML_TIMEOUT * len(pumls),
        )
    except (OSError, subprocess.SubprocessError) as e:
        console.print(f"[red]Falha ao executar o PlantUML: {e}[/red]")
        return 0
    rendered = sum(1 for p in pumls if p.with_suffix(".svg").is_file())
    if rendered < len(pumls):
        err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        detail = f": {err[-1]}" if err else ""
        console.print(
            f"[red]PlantUML renderizou {rendered}/{len(pumls)} "
            f"diagrama(s){detail}[/red]"
        )
    return rendered


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


def _embed_group(
    root: Path, key: str, members: dict[str, str], doc: str, pumls: list[Path]
) -> int:
    """Embed the group's source files, markdown doc and PlantUML diagrams into
    "<key>-meta/embeddings.json". Returns how many slices were embedded; on
    failure (e.g. the embedding model is missing) warns once and returns 0."""
    global _embed_warned
    entries: list[dict] = []

    def add(origin: str, kind: str, text: str) -> None:
        for i, chunk in enumerate(_slices(text)):
            entries.append(
                {"origin": origin, "kind": kind, "slice": i, "text": chunk}
            )

    for rel in sorted(members):
        try:
            add(rel, "source", (root / rel).read_text("utf-8", errors="replace"))
        except OSError:
            continue
    add(key + ".md", "doc", doc)
    for puml in pumls:
        try:
            add(puml.name, "diagram", puml.read_text("utf-8"))
        except OSError:
            continue
    if not entries:
        return 0

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
        return 0
    for entry, vector in zip(entries, vectors):
        entry["vector"] = vector
    out_dir = _meta_dir(root, key)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / EMBED_FILENAME).write_text(
        json.dumps({"records": entries}, ensure_ascii=False), "utf-8"
    )
    return len(entries)


def _compose_embeddings(root: Path, groups: dict[str, dict[str, str]]) -> int:
    """Merge every group's embeddings into .pythia/embeddings.json — the single
    index project_search loads. Returns the total number of indexed slices."""
    records: list[dict] = []
    for key in sorted(groups):
        try:
            data = json.loads(
                (_meta_dir(root, key) / EMBED_FILENAME).read_text("utf-8")
            )
        except (OSError, json.JSONDecodeError):
            continue
        for record in data.get("records", []):
            record["group"] = key
            records.append(record)
    index_path = root / PYTHIA_DIR / EMBED_FILENAME
    if not records:
        index_path.unlink(missing_ok=True)
        return 0
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps({"model": config.EMBED_MODEL, "records": records},
                   ensure_ascii=False),
        "utf-8",
    )
    return len(records)


def _generate_diagrams(
    root: Path, key: str, source: str, doc: str
) -> tuple[list[Path], int]:
    """Select and generate the group's PlantUML diagrams (selection by the
    doc model, then one forge-model call per diagram) into "<key>-meta/"
    beside the group's doc,
    showing each one in the chat as ASCII art and rendering all of them to
    .svg beside the .puml files. Returns (saved .puml paths, svgs rendered);
    the folder is always rebuilt, so stale diagrams never linger."""
    out_dir = _meta_dir(root, key)
    _clear_meta(out_dir)
    specs = _select_diagrams(source, doc)
    if not specs:
        return [], 0
    jar = _plantuml_jar()
    saved: list[Path] = []
    counters: dict[str, int] = {}
    for i, spec in enumerate(specs, 1):
        counters[spec["type"]] = counters.get(spec["type"], 0) + 1
        name = f"{spec['type']}-{counters[spec['type']]}"
        if _slug(spec["title"]):
            name += f"-{_slug(spec['title'])}"
        console.print(
            f"[bold yellow]🧩  ({i}/{len(specs)})[/bold yellow] "
            f"[cyan]{key}[/cyan] [dim]{spec['type']}: "
            f"{spec['title'] or '(sem título)'}[/dim]"
        )
        raw = _ask_streaming(
            config.FORGE_MODEL, DOC_DIAGRAM_GEN_SYS,
            (f"=== Diagram to produce ===\n"
             f"type: {spec['type']}\n"
             f"title: {spec['title'] or '(pick a fitting one)'}\n"
             f"must show: {spec['instructions'] or '(use your judgment)'}\n\n"
             f"{source}"),
            f"Diagrama {name}", f"[bold cyan]🧩  {key} · {name}[/bold cyan]",
        )
        puml = _normalize_plantuml(raw, spec["type"])
        if not puml:
            console.print(
                f"[red]O modelo não gerou o diagrama '{name}' de '{key}'.[/red]"
            )
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / (name + ".puml")).write_text(puml + "\n", "utf-8")
        saved.append(out_dir / (name + ".puml"))
        if jar is not None:
            txt = _render_txt(jar, puml)
            if txt:
                console.print(Text(txt))
    return saved, _render_svgs(jar, saved)


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

    # Docs whose source group disappeared entirely → remove them, along with
    # their "<key>-meta" folders.
    stale = [key for key in old_groups if key not in new_groups]
    for key in stale:
        _doc_path(root, key).unlink(missing_ok=True)
        _clear_meta(_meta_dir(root, key))
    _prune_empty_dirs(root / PYTHIA_DIR / DOCS_DIRNAME)

    # A group is (re)documented when any member is new, changed, or removed,
    # or when its doc file or embeddings are missing.
    todo = sorted(
        key for key, members in new_groups.items()
        if members != old_groups.get(key)
        or not _doc_path(root, key).is_file()
        or not (_meta_dir(root, key) / EMBED_FILENAME).is_file()
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
    diagrams_written = 0
    svgs_rendered = 0
    slices_embedded = 0
    for i, key in enumerate(todo, 1):
        console.print(f"[bold yellow]📚  ({i}/{len(todo)})[/bold yellow] [cyan]{key}[/cyan]")
        source = _group_source(root, new_groups[key])
        doc = _document_group(key, source)
        if doc:
            path = _doc_path(root, key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(doc + "\n", "utf-8")
            pumls, n_svg = _generate_diagrams(root, key, source, doc)
            diagrams_written += len(pumls)
            svgs_rendered += n_svg
            slices_embedded += _embed_group(root, key, new_groups[key], doc, pumls)
            persisted.update(new_groups[key])
        else:
            failed.append(key)
            # Failed groups stay out of the index so the next run retries them.
            for rel in new_groups[key]:
                persisted.pop(rel, None)
            console.print(f"[red]O modelo não gerou documentação para '{key}'.[/red]")
        _save_index(root, persisted)
    documented = [k for k in todo if k not in failed]

    project_doc = root / PYTHIA_DIR / PROJECT_DOC_FILENAME
    regenerated = False
    if documented or stale or not project_doc.is_file():
        console.print("[bold yellow]📖  Gerando a documentação geral do projeto...[/bold yellow]")
        regenerated = _write_project_doc(root, new_groups)

    # Compose the per-group embeddings into the single search index — only
    # when something actually changed since the last run (or it is missing).
    index_slices = -1
    if documented or stale or not (root / PYTHIA_DIR / EMBED_FILENAME).is_file():
        console.print("[bold yellow]🧠  Compondo o índice de busca...[/bold yellow]")
        index_slices = _compose_embeddings(root, new_groups)

    lines = [
        f"Project documentation updated under {root / PYTHIA_DIR}:",
        f"- {len(persisted)} file(s) hashed into {INDEX_FILENAME}",
        f"- {len(documented)} doc group(s) (re)written in {DOCS_DIRNAME}/",
        (f"- {diagrams_written} PlantUML diagram(s) written "
         f"({svgs_rendered} rendered to SVG) in *{META_SUFFIX}/ "
         f"folders beside the docs"),
        f"- {slices_embedded} text slice(s) embedded for semantic search",
        f"- {len(stale)} stale doc(s) removed",
        (f"- general documentation regenerated at {PROJECT_DOC_FILENAME}"
         if regenerated else "- general documentation unchanged"),
        (f"- search index composed at {EMBED_FILENAME} "
         f"({index_slices} slice(s) total)"
         if index_slices >= 0 else "- search index unchanged"),
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
