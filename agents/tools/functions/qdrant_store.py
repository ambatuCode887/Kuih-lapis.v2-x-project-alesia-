from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from agents.config import env, env_int


@dataclass(frozen=True)
class QdrantSettings:
    url: str
    api_key: str | None
    collection: str
    vector_size: int


def settings() -> QdrantSettings:
    return QdrantSettings(
        url=env("QDRANT_URL", "http://localhost:6333") or "http://localhost:6333",
        api_key=env("QDRANT_API_KEY") or None,
        collection=env("QDRANT_COLLECTION", "multi_agentic_rag") or "multi_agentic_rag",
        vector_size=env_int("EMBEDDING_DIM", 768),
    )


@lru_cache(maxsize=4)
def _cached_client(url: str, api_key: str | None):
    from qdrant_client import QdrantClient

    return QdrantClient(url=url, api_key=api_key)


def client():
    cfg = settings()
    return _cached_client(cfg.url, cfg.api_key)


def ensure_collection() -> str:
    from qdrant_client.models import Distance, VectorParams

    cfg = settings()
    qdrant = client()
    if not qdrant.collection_exists(cfg.collection):
        qdrant.create_collection(
            collection_name=cfg.collection,
            vectors_config=VectorParams(size=cfg.vector_size, distance=Distance.COSINE),
        )
    return cfg.collection


def upsert_points(points: list[Any]) -> dict[str, Any]:
    cfg = settings()
    qdrant = client()
    qdrant.upsert(collection_name=cfg.collection, points=points)
    return {"collection": cfg.collection, "upserted": len(points)}


def search(vector: list[float], limit: int = 5, score_threshold: float | None = None):
    cfg = settings()
    qdrant = client()
    if hasattr(qdrant, "search"):
        return qdrant.search(
            collection_name=cfg.collection,
            query_vector=vector,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )

    response = qdrant.query_points(
        collection_name=cfg.collection,
        query=vector,
        limit=limit,
        score_threshold=score_threshold,
        with_payload=True,
    )
    return response.points
