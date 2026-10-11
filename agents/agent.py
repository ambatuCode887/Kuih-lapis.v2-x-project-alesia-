from __future__ import annotations

import re
from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.llm_agent import Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.utils.context_utils import Aclosing

from agents.tools.agents.file_classifier.agent import file_classifier_agent
from agents.tools.agents.message_agents.agent import message_agent
from agents.tools.agents.url_check.agent import url_check_agent
from agents.config import agent_model, load_environment
from agents.tools.functions.ingest.documents import ingest_file_to_qdrant
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
_URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def should_route_to_retrieval(request: str) -> bool:
    """Return whether a request is a cybersecurity knowledge question."""
    normalized = request.casefold()
    if not normalized.strip() or _URL_PATTERN.search(normalized):
        return False
    if any(cue in normalized for cue in _ANALYSIS_CUES):
        return False
    return any(term in normalized for term in _CYBER_KNOWLEDGE_TERMS)


class RequestRouter(BaseAgent):
    """Deterministically route knowledge questions or artifact analysis."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        content = ctx.user_content
        request = " ".join(
            part.text
            for part in (content.parts if content else [])
            if getattr(part, "text", None)
        )
        target_name = (
            "retrieval_agent"
            if should_route_to_retrieval(request)
            else "analysis_agent"
        )
        target = next(
            (agent for agent in self.sub_agents if agent.name == target_name),
            None,
        )
        if target is None:
            raise RuntimeError(f"Configured route is missing agent: {target_name}")

        async with Aclosing(target.run_async(ctx)) as events:
            async for event in events:
                yield event


analysis_agent = Agent(
    model=agent_model(),
    name="analysis_agent",
    description="Orchestrates suspicious-message, link, and file analysis.",
    instruction=(
        "You orchestrate scam analysis. For a suspicious user message, delegate "
        "to message_agent. It analyzes the message and hands its structured risk "
        "score and confidence to its coordinator_agent child. The coordinator "
        "then delegates to clarification_agent when evidence is insufficient, "
        "or verification_agent when it is sufficient. For a link, domain or IP, "
        "delegate to url_check_agent, which checks reputation and also hands its "
        "result to its own coordinator_agent child. "
        "Do not bypass this chain. "
        "Preserve uncertainty and never claim unrun channel or source checks. "
        "Do not describe the result "
        "as a multi-channel assessment unless link or voice signals were actually "
        "provided. "
        "Use file_classifier_agent only when the complete matching pre-extracted "
        "feature vector is available; it cannot inspect raw files or URLs. "
        "Never present a model score as a confirmed fraud verdict."
    ),
    tools=[
        ingest_file_to_qdrant,
    ],
    sub_agents=[
        message_agent(),
        url_check_agent(),
        file_classifier_agent(),
    ],
)

root_agent = RequestRouter(
    name="root_agent",
    description=(
        "Routes cybersecurity knowledge questions directly to retrieval and "
        "suspicious artifact analysis to the analysis orchestrator."
    ),
    sub_agents=[analysis_agent, retrieval_agent()],
)
