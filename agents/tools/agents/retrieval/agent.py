from google.adk.agents.llm_agent import Agent

from agents.config import gemini_model
from agents.tools.functions.retrieve.credential_stuffing import retrieve_knowledge


def retrieval_agent() -> Agent:
    """Factory function to create a retrieval agent."""
    return Agent(
        model=gemini_model(),
        name="retrieval_agent",
        description="Retrieves relevant context from Qdrant-backed knowledge bases.",
        instruction=(
            "Use retrieve_knowledge to fetch grounded context before answering. "
            "Always mention the source and chunk index when results are available."
        ),
        tools=[retrieve_knowledge],
        mode="single_turn",
    )
