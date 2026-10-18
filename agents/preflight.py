"""Check the local stack before a run. Usage: python -m agents.preflight"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import httpx

from agents.config import DEFAULT_OLLAMA_MODEL, env, load_environment

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_QDRANT_COLLECTION = "multi_agentic_rag"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text:latest"
TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def normalize_model_name(name: str) -> str:
    # Ollama lists untagged models with an implicit ":latest" tag.
    return name if ":" in name else f"{name}:latest"


def missing_models(wanted: list[str], installed: list[str]) -> list[str]:
    available = {normalize_model_name(name) for name in installed}
    return [model for model in wanted if normalize_model_name(model) not in available]


def check_env() -> list[Check]:
    names = ["VTAI_TOKEN"]
    if (env("LLM_PROVIDER", "ollama") or "ollama").strip().lower() == "openrouter":
        names.append("OPENROUTER_API_KEY")
    if (env("EMBEDDING_PROVIDER", "google") or "google").strip().lower() == "google":
        names.append("GOOGLE_API_KEY")
    return [
        Check(f"env {name}", bool(env(name)), "set" if env(name) else "missing from .env")
        for name in names
    ]


def check_ollama(client: httpx.Client, base_url: str, wanted: list[str]) -> Check:
    try:
        response = client.get(f"{base_url}/api/tags")
        response.raise_for_status()
    except httpx.HTTPError as error:
        return Check("Ollama", False, f"not reachable at {base_url} ({type(error).__name__})")
    installed = [item.get("name", "") for item in response.json().get("models", [])]
    missing = missing_models(wanted, installed)
    if missing:
        return Check("Ollama", False, f"missing models: {', '.join(missing)} (run ollama pull)")
    return Check("Ollama", True, f"models ready: {', '.join(wanted)}")


def check_qdrant(client: httpx.Client, url: str, collection: str, api_key: str | None) -> Check:
    headers = {"api-key": api_key} if api_key else {}
    try:
        response = client.get(f"{url.rstrip('/')}/collections/{collection}", headers=headers)
    except httpx.HTTPError as error:
        return Check("Qdrant", False, f"not reachable at {url} ({type(error).__name__})")
    if response.status_code == 404:
        return Check("Qdrant", False, f"collection '{collection}' missing (run the ingest command)")
    if response.status_code != 200:
        return Check("Qdrant", False, f"HTTP {response.status_code} from {url}")
    points = response.json().get("result", {}).get("points_count", 0)
    if not points:
        return Check("Qdrant", False, f"collection '{collection}' is empty (run the ingest command)")
    return Check("Qdrant", True, f"collection '{collection}' has {points} points")


def check_backend(client: httpx.Client, url: str) -> Check:
    try:
        response = client.get(f"{url}/list-apps")
    except httpx.HTTPError:
        return Check("Backend", False, f"not running at {url} (start it before using the extension)", required=False)
    if response.status_code != 200:
        return Check("Backend", False, f"HTTP {response.status_code} from {url}", required=False)
    return Check("Backend", True, f"reachable at {url}", required=False)


def run_checks() -> list[Check]:
    load_environment()
    checks = check_env()

    wanted: list[str] = []
    if (env("LLM_PROVIDER", "ollama") or "ollama").strip().lower() == "ollama":
        wanted.append(env("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL) or DEFAULT_OLLAMA_MODEL)
    if (env("EMBEDDING_PROVIDER", "google") or "google").strip().lower() == "ollama":
        wanted.append(env("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL)
    ollama_url = (env("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL) or DEFAULT_OLLAMA_URL).rstrip("/")
    qdrant_url = env("QDRANT_URL", DEFAULT_QDRANT_URL) or DEFAULT_QDRANT_URL
    qdrant_collection = env("QDRANT_COLLECTION", DEFAULT_QDRANT_COLLECTION) or DEFAULT_QDRANT_COLLECTION
    qdrant_key = env("QDRANT_API_KEY") or None

    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        if wanted:
            checks.append(check_ollama(client, ollama_url, wanted))
        checks.append(check_qdrant(client, qdrant_url, qdrant_collection, qdrant_key))
        checks.append(check_backend(client, DEFAULT_BACKEND_URL))
    return checks


def main() -> int:
    checks = run_checks()
    for check in checks:
        status = "OK" if check.ok else ("FAIL" if check.required else "WARN")
        print(f"[{status}] {check.name}: {check.detail}")
    return 0 if all(check.ok or not check.required for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
