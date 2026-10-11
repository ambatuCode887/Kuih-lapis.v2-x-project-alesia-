from pathlib import Path

from google.adk.agents.llm_agent import Agent

from agents.config import agent_model


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
		mode="single_turn",
	)
