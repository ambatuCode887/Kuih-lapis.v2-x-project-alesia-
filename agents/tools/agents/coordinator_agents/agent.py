from pathlib import Path

from google.adk.agents.llm_agent import Agent

from agents.config import gemini_model
from agents.tools.agents.clarification_agents.agent import clarification_agent
from agents.tools.agents.url_check.agent import url_check_agent
from agents.tools.agents.verification_agents.agent import verification_agent


_PROMPT = Path(__file__).parent / "prompt.md"


def coordinator_agent() -> Agent:
	"""Create the sub-agent for combining scam-analysis signals."""
	return Agent(
		model=gemini_model(),
		name="coordinator_agent",
		description=(
			"Combines supplied message, link, and transcript analysis signals "
			"into an evidence-based risk assessment and confidence level."
		),
		instruction=_PROMPT.read_text(encoding="utf-8"),
		sub_agents=[
			clarification_agent(),
			url_check_agent(),
			verification_agent(),
		],
		mode="single_turn",
	)



