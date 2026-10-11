from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from agents.tools.agents.file_classifier.agent import file_classifier_agent

from agents.config import load_environment
from agents.tools.agents.retrieval.agent import retrieval_agent
from agents.tools.functions.ingest.documents import ingest_file_to_qdrant
from agents.tools.functions.retrieve.credential_stuffing import retrieve_knowledge
from pathlib import Path

load_environment()

root_agent = Agent(
    model="gemini-3.5-flash",
    name="root_agent",
    description="Multi-agent RAG assistant with Qdrant retrieval and Confluence publishing.",
    instruction=(
        "You coordinate a multi-agent RAG workflow. Use ingestion tools to add "
        "documents to Qdrant, retrieval tools to ground answers, summary agents "
        "to prepare Confluence-ready Markdown, and publisher tools only after "
        "running a dry run unless the user explicitly asks to publish."
    ),
    tools=[
        ingest_file_to_qdrant,
        retrieve_knowledge,
    ],
    sub_agents=[
        retrieval_agent(),
        file_classifier_agent(),
    ],
)
