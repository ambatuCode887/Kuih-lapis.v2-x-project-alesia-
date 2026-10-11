from pathlib import Path

from google.adk.agents.llm_agent import Agent

from agents.config import gemini_model
from agents.tools.functions.retrieve.credential_stuffing import retrieve_knowledge


_PROMPT = Path(__file__).parent / "prompt.md"


def verification_agent() -> Agent:
	"""Create the sub-agent for scam-pattern retrieval and verification guidance."""
	return Agent(
		model=gemini_model(),
		name="verification_agent",
		description=(
			"Checks supplied scam indicators against the internal knowledge base "
			"and guides users through independent official verification."
		),
		instruction=_PROMPT.read_text(encoding="utf-8"),
		tools=[retrieve_knowledge],
		mode="single_turn",
	)

