"""Build the suggestion chips in the extension from the questions ingested into Qdrant.

Run after ingesting Q&A documents: python -m agents.tools.functions.ingest.suggestions
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.tools.functions.qdrant_store import client, settings

ROOT = Path(__file__).resolve().parents[4]
OUTPUT = ROOT / "extension" / "lib" / "suggestions.json"
PAGE_SIZE = 256


def ingested_questions() -> list[str]:
    """Return unique `question` payloads only; answers and chunk text are never read."""
    qdrant = client()
    collection = settings().collection
    questions: dict[str, None] = {}
    offset = None
    while True:
        points, offset = qdrant.scroll(
            collection_name=collection,
            limit=PAGE_SIZE,
            offset=offset,
            with_payload=["question"],
            with_vectors=False,
        )
        for point in points:
            question = (point.payload or {}).get("question")
            if isinstance(question, str) and question.strip():
                questions.setdefault(question.strip(), None)
        if offset is None:
            break
    return list(questions)


def main() -> int:
    questions = ingested_questions()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(questions, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(questions)} question(s) to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
