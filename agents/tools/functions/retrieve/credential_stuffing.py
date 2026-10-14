from __future__ import annotations

from pathlib import PureWindowsPath
from typing import Any

from agents.tools.functions.embeddings import embed_text
from agents.tools.functions.qdrant_store import search


def _public_source_label(source: Any) -> str:
    if not isinstance(source, str):
        return ""
    return PureWindowsPath(source).name


def retrieve_knowledge(
    query: str,
    limit: int = 5,
    score_threshold: float | None = None,
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
    hits = search(vector=vector, limit=limit, score_threshold=score_threshold)
    results = []
    for hit in hits:
        payload = hit.payload or {}
        results.append(
            {
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
        )
    return {"query": query, "results": results}
