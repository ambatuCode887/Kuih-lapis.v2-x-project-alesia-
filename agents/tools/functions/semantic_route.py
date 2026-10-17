from __future__ import annotations

import logging
import math
from functools import lru_cache

from agents.config import env
from agents.tools.functions.embeddings import embed_texts

logger = logging.getLogger(__name__)

# Kept separate from the routing eval set so the eval stays a fair test.
_EXEMPLARS: dict[str, tuple[str, ...]] = {
    "retrieval_agent": (
        "What steps help protect a household from online fraud?",
        "Explain what a brute force attack is.",
        "How should I choose a strong passphrase?",
        "What is the difference between a virus and a worm?",
        "Give general advice on keeping smart home devices secure.",
        "How does end-to-end encryption protect messages?",
        "What should an employee know about workplace cyber hygiene?",
        "How do password managers work and are they safe?",
        "Why do security teams patch software quickly?",
        "What are the warning signs of a social engineering attack?",
    ),
    "message_agent": (
        "Here is a text I got. Does it look like a scam to you?",
        "My bank emailed me with a link. Can you tell if it is genuine?",
        "A stranger on social media is asking me to send money. Is this legit?",
        "I got a call asking for my verification code, what do I do?",
        "Someone texted me a prize notice. Is it fake?",
        "Please look at this message from my employer and tell me if it is safe.",
        "This screenshot claims my account is locked. Is it real?",
        "A courier message says I owe a fee. Should I pay it?",
        "Is this invoice email trying to trick me into paying a fake bill?",
        "Check whether this WhatsApp message asking for gift cards is a scam.",
    ),
}


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


@lru_cache(maxsize=1)
def _exemplar_vectors() -> dict[str, list[list[float]]]:
    labelled = [(route, text) for route, texts in _EXEMPLARS.items() for text in texts]
    vectors = embed_texts([text for _, text in labelled])
    grouped: dict[str, list[list[float]]] = {route: [] for route in _EXEMPLARS}
    for (route, _), vector in zip(labelled, vectors):
        grouped[route].append(vector)
    return grouped


def semantic_knowledge_route(request: str) -> str:
    """Pick retrieval or message by nearest exemplar; message_agent when unsure or on failure."""
    provider = (env("EMBEDDING_PROVIDER", "google") or "google").lower()
    if provider == "fake":
        # Hash embeddings carry no meaning, so keep offline runs deterministic.
        return "message_agent"
    try:
        query = embed_texts([request])[0]
        exemplars = _exemplar_vectors()
    except RuntimeError as error:
        logger.warning("Semantic routing unavailable, defaulting to message_agent: %s", error)
        return "message_agent"

    best = {
        route: max(_cosine(query, vector) for vector in vectors)
        for route, vectors in exemplars.items()
    }
    return "retrieval_agent" if best["retrieval_agent"] > best["message_agent"] else "message_agent"
