from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - allows lightweight syntax/smoke checks
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_ROOT = Path(__file__).resolve().parent
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3.5-lightning:free"
DEFAULT_GOOGLE_MODEL = "gemini-3.5-flash"


def project_env_path() -> Path | None:
    """Return the preferred project environment file, if present."""
    for candidate in (AGENTS_ROOT / ".env", PROJECT_ROOT / ".env"):
        if candidate.exists():
            return candidate
    return None


def load_environment() -> None:
    """Load project env files without overriding process-level secrets."""
    for path in (PROJECT_ROOT / ".env", AGENTS_ROOT / ".env"):
        if path.exists():
            load_dotenv(path, override=False)


def env(name: str, default: str | None = None) -> str | None:
    load_environment()
    return os.getenv(name, default)


def agent_model():
    provider = (env("LLM_PROVIDER", "google") or "google").strip().lower()
    fallback_provider = (env("LLM_FALLBACK_PROVIDER", "") or "").strip().lower()
    if fallback_provider and provider != "google":
        raise ValueError("LLM_FALLBACK_PROVIDER is currently supported only with LLM_PROVIDER=google.")
    if provider == "google":
        required_env("GOOGLE_API_KEY")
        model_name = (env("LLM_MODEL", DEFAULT_GOOGLE_MODEL) or DEFAULT_GOOGLE_MODEL).strip()
        if not fallback_provider:
            return model_name
        if fallback_provider != "openrouter":
            raise ValueError("LLM_FALLBACK_PROVIDER must be empty or 'openrouter'.")

        from google.adk.models.google_llm import Gemini
        from google.adk.models.lite_llm import LiteLlm

        from agents.model_failover import FailoverLlm

        fallback_name = env("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL) or DEFAULT_OPENROUTER_MODEL
        required_env("OPENROUTER_API_KEY")
        return FailoverLlm(
            model=model_name,
            primary_model=Gemini(model=model_name),
            fallback_model=LiteLlm(
                model=f"openrouter/{fallback_name.strip() or DEFAULT_OPENROUTER_MODEL}",
                drop_params=True,
            ),
        )

    from google.adk.models.lite_llm import LiteLlm

    if provider == "openrouter":
        model_name = (env("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL) or "").strip()
        required_env("OPENROUTER_API_KEY")
        return LiteLlm(model=f"openrouter/{model_name or DEFAULT_OPENROUTER_MODEL}")
    if provider != "ollama":
        raise ValueError("LLM_PROVIDER must be 'google', 'ollama', or 'openrouter'.")

    model_name = (env("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL) or "").strip()
    base_url = (env("OLLAMA_BASE_URL", "http://localhost:11434") or "").strip()
    return LiteLlm(
        model=f"ollama_chat/{model_name or DEFAULT_OLLAMA_MODEL}",
        api_base=base_url or "http://localhost:11434",
    )


def required_env(name: str) -> str:
    value = env(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def env_int(name: str, default: int) -> int:
    value = env(name)
    if value is None or value == "":
        return default
    return int(value)


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def missing(names: Iterable[str]) -> list[str]:
    return [name for name in names if not env(name)]
