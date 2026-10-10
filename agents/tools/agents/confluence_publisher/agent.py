from google.adk.agents.llm_agent import Agent

from pathlib import Path

from agents.tools.functions.publish.prepare import prepare_confluence_page
from agents.tools.functions.publish.result import publish_confluence_page

_PROMPT = Path(__file__).parent / "prompt.md"

def confluence_publisher_agent() -> Agent:
    """Creates an agent for preparing and publishing Confluence pages."""
    return Agent(
        model="gemini-3.5-flash",
        name="confluence_publisher_agent",
        description="Prepares and publishes Confluence pages.",
        instruction=_PROMPT.read_text(encoding="utf-8"),
        tools=[prepare_confluence_page, publish_confluence_page],
        mode="single_turn",
    )