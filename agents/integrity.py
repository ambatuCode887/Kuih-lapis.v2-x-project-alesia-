"""Fingerprints of every agent's description and instruction, checked at startup."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path(__file__).resolve().parent / "agent_manifest.json"
# Only the manifest update command sets this. Setting it in production disables the check.
UPDATE_ENV = "AGENT_MANIFEST_UPDATE"
UPDATE_HINT = "Run: .\\.venv\\Scripts\\python -m agents.integrity"


def _digest(value: object) -> str:
    if not isinstance(value, str):
        return "non-text"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _all_agents(root: Any) -> list[Any]:
    found: list[Any] = []
    pending = [root]
    while pending:
        agent = pending.pop()
        found.append(agent)
        pending.extend(getattr(agent, "sub_agents", None) or [])
    return found


def fingerprints(root: Any) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for agent in _all_agents(root):
        name = agent.name
        if name in result:
            raise ValueError(f"Duplicate agent name: {name}")
        result[name] = {
            "description": _digest(getattr(agent, "description", "") or ""),
            "instruction": _digest(getattr(agent, "instruction", "") or ""),
        }
    return result


def write_manifest(root: Any) -> None:
    text = json.dumps(fingerprints(root), indent=2, sort_keys=True)
    MANIFEST_PATH.write_text(text + "\n", encoding="utf-8")


def verify_agent_definitions(root: Any) -> None:
    if os.getenv(UPDATE_ENV) == "1":
        return
    if not MANIFEST_PATH.exists():
        raise RuntimeError(f"Agent manifest is missing. {UPDATE_HINT}")
    expected = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    actual = fingerprints(root)
    changed = sorted(
        name
        for name in set(expected) | set(actual)
        if expected.get(name) != actual.get(name)
    )
    if changed:
        raise RuntimeError(
            "Agent definitions changed without updating the manifest: "
            f"{', '.join(changed)}. {UPDATE_HINT}"
        )


if __name__ == "__main__":
    os.environ[UPDATE_ENV] = "1"
    from agents.agent import root_agent

    write_manifest(root_agent)
    print(f"Wrote {MANIFEST_PATH}")
