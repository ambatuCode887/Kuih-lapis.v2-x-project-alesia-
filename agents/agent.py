from __future__ import annotations

import re
from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.utils.context_utils import Aclosing

from agents.tools.agents.file_classifier.agent import file_classifier_agent
from agents.tools.agents.message_agents.agent import message_agent
from agents.tools.agents.url_check.agent import url_check_agent
from agents.config import load_environment
from agents.tools.agents.retrieval.agent import retrieval_agent

load_environment()

_CYBER_KNOWLEDGE_TERMS = (
    "cybersecurity",
    "cyber security",
    "malware",
    "virus",
    "ransomware",
    "phishing",
    "scam",
    "credential stuffing",
    "password",
    "public wi-fi",
    "public wifi",
    "firewall",
    "encryption",
    "vpn",
    "multi-factor",
    "mfa",
    "data breach",
    "network security",
    "antivirus",
    "spyware",
    "trojan",
    "identity theft",
    "social engineering",
    "hacking",
    "security risk",
)
_ANALYSIS_CUES = (
    "analyze this",
    "analyse this",
    "check this",
    "review this",
    "inspect this",
    "classify this",
    "score this",
    "i received",
    "i got this",
    "someone sent me",
    "this email",
    "this message",
    "this link",
    "this file",
)
_URL_ANALYSIS_CUES = (
    "check this domain",
    "check this ip",
    "analyze this url",
    "analyse this url",
    "url reputation",
    "domain reputation",
    "ip reputation",
    "scan this link",
    "look up this domain",
)
_FEATURE_VECTOR_CUES = (
    "feature vector",
    "precomputed features",
    "pre-extracted features",
)
_URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def should_route_to_retrieval(request: str) -> bool:
    """Return whether a request is a cybersecurity knowledge question."""
    normalized = request.casefold()
    if not normalized.strip() or _URL_PATTERN.search(normalized):
        return False
    if any(cue in normalized for cue in _ANALYSIS_CUES):
        return False
    return any(term in normalized for term in _CYBER_KNOWLEDGE_TERMS)


def route_request_to_agent(request: str) -> str:
    """Choose a specialist directly, without an LLM orchestration layer."""
    normalized = request.casefold()
    if should_route_to_retrieval(request):
        return "retrieval_agent"
    if _URL_PATTERN.search(normalized) or any(
        cue in normalized for cue in _URL_ANALYSIS_CUES
    ):
        return "url_check_agent"
    if any(cue in normalized for cue in _FEATURE_VECTOR_CUES):
        return "file_classifier_agent"
    return "message_agent"


class RequestRouter(BaseAgent):
    """Deterministically route requests to the appropriate specialist."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        content = ctx.user_content
        request = " ".join(
            part.text
            for part in (content.parts if content else [])
            if getattr(part, "text", None)
        )
        target_name = route_request_to_agent(request)
        target = next(
            (agent for agent in self.sub_agents if agent.name == target_name),
            None,
        )
        if target is None:
            raise RuntimeError(f"Configured route is missing agent: {target_name}")

        async with Aclosing(target.run_async(ctx)) as events:
            async for event in events:
                yield event


root_agent = RequestRouter(
    name="root_agent",
    description=(
        "Routes requests directly to message analysis, URL reputation, "
        "precomputed-file classification, or knowledge retrieval specialists."
    ),
    sub_agents=[
        message_agent(),
        url_check_agent(),
        file_classifier_agent(),
        retrieval_agent(),
    ],
)
