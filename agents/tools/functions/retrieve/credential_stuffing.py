from __future__ import annotations

from pathlib import PureWindowsPath
from typing import Any

from agents.tools.functions.embeddings import embed_text
from agents.tools.functions.qdrant_store import search


def _public_source_label(source: Any) -> str:
    if not isinstance(source, str):
        return ""
    return PureWindowsPath(source).name


# Minimum cosine similarity for a chunk to count as evidence. Measured on
# on-topic questions (top hits 0.73+) vs. an off-topic question (top hit 0.59).
DEFAULT_SCORE_THRESHOLD = 0.65


def retrieve_knowledge(
    query: str,
    limit: int = 5,
    score_threshold: float | None = DEFAULT_SCORE_THRESHOLD,
) -> dict[str, Any]:
    """Retrieve relevant RAG chunks from Qdrant for a user query."""
    if isinstance(score_threshold, str):
        normalized_threshold = score_threshold.strip()
        if normalized_threshold.casefold() in {"", "none", "null"}:
            score_threshold = None
        else:
            try:
                score_threshold = float(normalized_threshold)
            except ValueError as error:
                raise ValueError("score_threshold must be a number or null.") from error

    vector = embed_text(query)
    try:
        hits = search(vector=vector, limit=limit, score_threshold=score_threshold)
    except Exception as error:
        raise RuntimeError(
            "Qdrant search failed. Check that Qdrant is running and QDRANT_URL is correct."
        ) from error
    return {"query": query, "results": [_hit_to_result(hit) for hit in hits]}


def format_passage(index: int, result: dict[str, Any]) -> str:
    source = result.get("source") or "unknown source"
    chunk_index = result.get("chunk_index")
    category = (result.get("metadata") or {}).get("category")
    header = f"[{index}] Source: {source}"
    if chunk_index is not None:
        header += f", chunk {chunk_index}"
    if category:
        header += f" (category: {category})"
    return f"{header}\n{result.get('text', '')}"


def _hit_to_result(hit: Any) -> dict[str, Any]:
    payload = hit.payload or {}
    return {
        "score": hit.score,
        "text": payload.get("text", ""),
        "source": _public_source_label(payload.get("source", "")),
        "chunk_index": payload.get("chunk_index"),
        "metadata": {
            key: value
            for key, value in payload.items()
            if key not in {"text", "source", "chunk_index"}
            and not key.casefold().endswith("_path")
        },
    }
