"""Smoke-check local chunking."""

from __future__ import annotations

from agents.config import load_environment
from agents.tools.functions.ingest.documents import chunk_text


def main() -> None:
    load_environment()
    chunks = chunk_text("Credential stuffing is an attack using leaked passwords." * 20)
    assert chunks, "chunk_text should produce chunks"
    print("Smoke checks passed.")


if __name__ == "__main__":
    main()
