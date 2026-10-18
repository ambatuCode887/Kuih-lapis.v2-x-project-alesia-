import json

from google.adk.events.event import Event
from google.genai import types

from agents.agent import _hide_specialist_text
from agents.tools.agents.verification_agents import agent as verification_agent_module
from agents.tools.functions.retrieve.credential_stuffing import (
    DEFAULT_SCORE_THRESHOLD,
)


def test_hidden_specialist_assessment_is_preserved_as_event_metadata() -> None:
    assessment = {
        "risk_score": 82,
        "risk_level": "high",
        "confidence": 88,
        "indicators": [
            {
                "type": "credential_request",
                "evidence": "Enter your password",
                "reason": "A password request in an unexpected message is suspicious.",
            }
        ],
        "assessment": "The message asks for a password through an unexpected link.",
        "recommended_actions": ["Do not enter your password through the link."],
    }
    event = Event(
        author="message_agent",
        invocation_id="image-check-test",
        content=types.Content(
            role="model",
            parts=[types.Part(text=json.dumps(assessment))],
        ),
    )

    _hide_specialist_text(event)

    assert event.content is None
    assert event.custom_metadata == {"assessment": assessment}


def test_verification_retrieval_cannot_disable_relevance_threshold(monkeypatch) -> None:
    actual_args: dict[str, object] = {}

    def fake_retrieve_knowledge(**kwargs: object) -> dict[str, object]:
        actual_args.update(kwargs)
        return {"query": kwargs["query"], "results": []}

    monkeypatch.setattr(
        verification_agent_module,
        "retrieve_knowledge",
        fake_retrieve_knowledge,
    )

    result = verification_agent_module.retrieve_verification_knowledge(
        "bank message asks for a password"
    )

    assert result["results"] == []
    assert actual_args == {
        "query": "bank message asks for a password",
        "limit": 3,
        "score_threshold": DEFAULT_SCORE_THRESHOLD,
    }
