from __future__ import annotations

from typing import Any

from agents.tools.functions.embeddings import embed_text
from agents.tools.functions.qdrant_store import search


def retrieve_knowledge(
    query: str,
    limit: int = 5,
    score_threshold: float | None = None,
) -> dict[str, Any]:
    """Retrieve relevant RAG chunks from Qdrant for a user query."""
    vector = embed_text(query)
    hits = search(vector=vector, limit=limit, score_threshold=score_threshold)
    results = []
    for hit in hits:
        payload = hit.payload or {}
        results.append(
            {
                "score": hit.score,
                "text": payload.get("text", ""),
                "source": payload.get("source", ""),
                "chunk_index": payload.get("chunk_index"),
                "metadata": {
                    key: value
                    for key, value in payload.items()
                    if key not in {"text", "source", "chunk_index"}
                },
            }
        )
    return {"query": query, "results": results}
