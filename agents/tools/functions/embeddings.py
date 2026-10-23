from __future__ import annotations

import hashlib
import math
from typing import Sequence

from agents.config import env, env_int

GOOGLE_EMBEDDING_BATCH_SIZE = 100
OLLAMA_EMBEDDING_BATCH_SIZE = 16


def _hash_embedding(text: str, dimension: int) -> list[float]:
    values: list[float] = []
    counter = 0
    while len(values) < dimension:
        digest = hashlib.sha256(f"{counter}:{text}".encode("utf-8")).digest()
        for byte in digest:
            values.append((byte / 127.5) - 1.0)
            if len(values) == dimension:
                break
        counter += 1

    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed texts for Qdrant.

    Set `EMBEDDING_PROVIDER=fake` for offline smoke tests or `ollama` to use
    the local Ollama embedding model. The default uses Google GenAI embeddings.
    """
    dimension = env_int("EMBEDDING_DIM", 768)
    provider = (env("EMBEDDING_PROVIDER", "google") or "google").lower()
    if provider == "fake":
        return [_hash_embedding(text, dimension) for text in texts]
    if not texts:
        return []

    if provider == "ollama":
        import httpx

        model = (env("EMBEDDING_MODEL", "nomic-embed-text:latest") or "nomic-embed-text:latest").strip()
        base_url = (env("OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434").rstrip("/")
        embeddings = []
        try:
            with httpx.Client(timeout=120.0) as ollama_client:
                for start in range(0, len(texts), OLLAMA_EMBEDDING_BATCH_SIZE):
                    batch = list(texts[start : start + OLLAMA_EMBEDDING_BATCH_SIZE])
                    response = ollama_client.post(
                        f"{base_url}/api/embed",
                        json={"model": model, "input": batch},
                    )
                    response.raise_for_status()
                    batch_embeddings = response.json().get("embeddings")
                    if not isinstance(batch_embeddings, list) or len(batch_embeddings) != len(batch):
                        raise RuntimeError("Ollama embedding response did not match the input batch.")
                    if any(len(vector) != dimension for vector in batch_embeddings):
                        raise RuntimeError(
                            f"Ollama returned an embedding with a dimension other than {dimension}."
                        )
                    embeddings.extend([list(vector) for vector in batch_embeddings])
        except Exception as error:
            raise RuntimeError(
                f"Ollama embedding request failed for model '{model}'. "
                "Check that Ollama is running and the model is installed."
            ) from error
        return embeddings

    from google import genai

    client = genai.Client(api_key=env("GOOGLE_API_KEY"))
    model = env("EMBEDDING_MODEL", "gemini-embedding-001") or "gemini-embedding-001"
    try:
        embeddings = []
        for start in range(0, len(texts), GOOGLE_EMBEDDING_BATCH_SIZE):
            batch = texts[start : start + GOOGLE_EMBEDDING_BATCH_SIZE]
            response = client.models.embed_content(
                model=model,
                contents=list(batch),
                config={"output_dimensionality": dimension},
            )
            batch_embeddings = getattr(response, "embeddings", None)
            if batch_embeddings is None:
                raise RuntimeError("Google embedding response did not include embeddings.")
            embeddings.extend(list(item.values) for item in batch_embeddings)
    except Exception as error:
        raise RuntimeError(
            f"Embedding request failed for model '{model}'. "
            "Set EMBEDDING_MODEL to an available Google embedding model "
            "or use EMBEDDING_PROVIDER=fake for offline tests."
        ) from error
    return embeddings


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
