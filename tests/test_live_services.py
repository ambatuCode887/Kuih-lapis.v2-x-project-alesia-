from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.agent import root_agent
from agents.config import env
from agents.tools.functions.retrieve import credential_stuffing
from agents.tools.functions.retrieve.credential_stuffing import format_passage, retrieve_knowledge

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLOSED_PORT_URL = "http://127.0.0.1:1"


def _reachable(url: str) -> bool:
    try:
        httpx.get(url, timeout=2.0)
    except httpx.HTTPError:
        return False
    return True


OLLAMA_UP = _reachable(env("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/") + "/api/tags")
QDRANT_UP = _reachable(env("QDRANT_URL", "http://localhost:6333").rstrip("/") + "/collections")
NEEDS_BOTH_SERVICES = pytest.mark.skipif(
    not (OLLAMA_UP and QDRANT_UP),
    reason="Ollama and Qdrant must both be running for this live test.",
)

_TURN_RUNNER = r"""
import asyncio, json, sys
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agents.agent import root_agent

async def run(messages):
    service = InMemorySessionService()
    runner = Runner(app_name="agents", agent=root_agent, session_service=service)
    await service.create_session(app_name="agents", user_id="u", session_id="s")
    replies = []
    for message in messages:
        texts = []
        async for event in runner.run_async(
            user_id="u",
            session_id="s",
            new_message=types.Content(role="user", parts=[types.Part(text=message)]),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                texts.append(event.content.parts[0].text or "")
        replies.append(texts)
    return replies

print(json.dumps(asyncio.run(run(json.loads(sys.argv[1])))))
"""


def test_model_outage_returns_safe_reply_in_fresh_process() -> None:
    message = "Analyze this message: URGENT verify your OTP now or your account is suspended"
    result = subprocess.run(
        [sys.executable, "-c", _TURN_RUNNER, json.dumps([message])],
        cwd=PROJECT_ROOT,
        env={**os.environ, "OLLAMA_BASE_URL": CLOSED_PORT_URL},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        check=False,
    )

    assert result.returncode == 0, result.stderr[-2000:]
    replies = json.loads(result.stdout.strip().splitlines()[-1])
    final_texts = [text for turn in replies for text in turn if text.strip()]
    assert final_texts, "the user must always receive a final reply"
    assert "couldn't complete a reliable assessment" in final_texts[-1]


def test_qdrant_outage_raises_clear_runtime_error(monkeypatch) -> None:
    monkeypatch.setenv("QDRANT_URL", CLOSED_PORT_URL)
    monkeypatch.setattr(credential_stuffing, "embed_text", lambda text: [0.0] * 768)

    with pytest.raises(RuntimeError, match="Qdrant search failed"):
        retrieve_knowledge("What is credential stuffing?")


@NEEDS_BOTH_SERVICES
def test_live_passages_use_readable_citations() -> None:
    result = retrieve_knowledge("How do I dispose of sensitive documents?", limit=2)
    passages = [format_passage(index, hit) for index, hit in enumerate(result["results"], start=1)]

    assert passages
    for passage in passages:
        header = passage.splitlines()[0]
        assert header.startswith("[") and "Source: " in header and ", chunk " in header
        assert "source=" not in passage
        assert "score=" not in passage


async def _chat(runner: Runner, message: str) -> list:
    return [
        event
        async for event in runner.run_async(
            user_id="live-user",
            session_id="live-session",
            new_message=types.Content(role="user", parts=[types.Part(text=message)]),
        )
    ]


@NEEDS_BOTH_SERVICES
def test_live_related_question_returns_cached_answer(monkeypatch) -> None:
    monkeypatch.setattr("agents.agent._CACHED_FOLLOWUP_DELAY_SECONDS", 0)

    async def scenario():
        service = InMemorySessionService()
        runner = Runner(app_name="agents", agent=root_agent, session_service=service)
        await service.create_session(
            app_name="agents", user_id="live-user", session_id="live-session"
        )
        first = await _chat(runner, "How do I dispose of sensitive documents?")
        related = [
            question
            for event in first
            if (event.custom_metadata or {}).get("kind") == "related_questions"
            for question in event.custom_metadata["questions"]
        ]
        assert related, "the first answer must offer related questions"
        second = await _chat(runner, related[0])
        return second

    second = asyncio.run(scenario())
    final = [event for event in second if event.is_final_response() and event.content]
    text = final[-1].content.parts[0].text
    assert "Source:" in text
    assert "chunk" in text
