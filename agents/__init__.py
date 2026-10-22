"""Project package for the multi-agent RAG assistant."""

from .config import load_environment

# Load .env at import so libraries that read os.environ directly see the values.
load_environment()