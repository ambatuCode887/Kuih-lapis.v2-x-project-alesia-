from pathlib import Path

from google.adk.agents.llm_agent import Agent

from agents.config import agent_model
from agents.tools.agents.coordinator_agents.agent import coordinator_agent


_PROMPT = Path(__file__).parent / "prompt.md"


def message_agent() -> Agent:
	"""Create the sub-agent for analyzing suspicious messages."""
	return Agent(
		model=agent_model(),
		name="message_agent",
		description=(
			"Analyzes user-provided messages for scam and spam indicators, "
			"with evidence-based risk guidance."
		),
		instruction=_PROMPT.read_text(encoding="utf-8"),
		sub_agents=[coordinator_agent()],
		mode="single_turn",
	)
