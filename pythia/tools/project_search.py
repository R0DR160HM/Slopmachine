"""project_search: semantic search over the project's documentation index.

Embeds the query with the same model used by write_project_documentation and
returns the best-matching slices of source code, markdown docs and PlantUML
diagrams from .pythia/embeddings.json as extra context for the agent. When
the index does not exist yet, the returned message instructs the agent to
tell the user to build the docs first.
"""

import json
import math
from pathlib import Path

from pythia.config import EMBED_MODEL, SEARCH_TOP_K
from pythia.llm import embed_query
from pythia.tools.documentation import EMBED_FILENAME, PYTHIA_DIR

MISSING_INDEX_MESSAGE = (
    "The project documentation has not been generated yet, so there is no "
    "search index to look in. Tell the user to first ask you to create the "
    "docs (by sending the message 'docs'); that builds the documentation and "
    "the search index. Then project_search can be used."
)


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def project_search(query: str) -> str:
    """The indexed slices most similar to `query`, formatted as extra context
    for the model — or the instruction to build the docs when there is no
    index for the project in the current working directory."""
    path = Path.cwd() / PYTHIA_DIR / EMBED_FILENAME
    try:
        records = json.loads(path.read_text("utf-8")).get("records", [])
    except (OSError, json.JSONDecodeError):
        records = []
    if not records:
        return MISSING_INDEX_MESSAGE

    try:
        vector = embed_query(query)
    except Exception as e:
        return (
            f"project_search could not embed the query ({e}). Check that the "
            f"'{EMBED_MODEL}' model is available in Ollama."
        )

    scored = sorted(
        ((_cosine(vector, record.get("vector", [])), record)
         for record in records),
        key=lambda pair: pair[0],
        reverse=True,
    )[:SEARCH_TOP_K]

    sections = []
    for score, record in scored:
        sections.append(
            f"=== {record.get('kind', '?')} · {record.get('origin', '?')} "
            f"(unit: {record.get('group', '?')}) · slice {record.get('slice', 0)} "
            f"· relevance {score:.2f} ===\n{record.get('text', '')}"
        )
    return "\n\n".join(sections)
