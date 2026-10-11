from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from agents.tools.agents.file_classifier.agent import file_classifier_agent
from agents.tools.agents.message_agents.agent import message_agent
from agents.config import gemini_model, load_environment
from agents.tools.functions.ingest.documents import ingest_file_to_qdrant
from agents.tools.functions.retrieve.credential_stuffing import retrieve_knowledge

load_environment()

root_agent = Agent(
    model=gemini_model(),
    name="root_agent",
    description="Scam-awareness assistant with message analysis, file scoring, and Qdrant retrieval.",
    instruction=(
        "You orchestrate scam analysis. For a suspicious user message, delegate "
        "to message_agent. It analyzes the message and hands its structured risk "
        "score and confidence to its coordinator_agent child. The coordinator "
        "then delegates to clarification_agent when evidence is insufficient, "
        "or verification_agent when it is sufficient. When the message contains a "
        "link, the coordinator first uses url_check_agent for domain reputation. "
        "Do not bypass this chain. "
        "Preserve uncertainty and never claim unrun channel or source checks. "
        "Do not describe the result "
        "as a multi-channel assessment unless link or voice signals were actually "
        "provided. "
        "Use retrieval tools when scam-pattern knowledge can help ground guidance. "
        "Use file_classifier_agent only when the complete matching pre-extracted "
        "feature vector is available; it cannot inspect raw files or URLs. "
        "Never present a model score as a confirmed fraud verdict."
    ),
    tools=[
        ingest_file_to_qdrant,
        retrieve_knowledge,
    ],
    sub_agents=[
        message_agent(),
        file_classifier_agent(),
    ],
)
