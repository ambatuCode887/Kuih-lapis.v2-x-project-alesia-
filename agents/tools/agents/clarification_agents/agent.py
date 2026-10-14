from pathlib import Path

from google.adk.agents.llm_agent import Agent

from agents.config import agent_model
from agents.tools.agents.message_agents.attachments import isolate_current_turn

_PROMPT = Path(__file__).parent / "prompt.md"


def clarification_agent() -> Agent:
	"""Create the sub-agent for generating focused scam-analysis questions."""
	return Agent(
		model=agent_model(),
		name="clarification_agent",
		description=(
			"Suggests one or two privacy-conscious follow-up questions when "
			"scam-analysis evidence is incomplete or ambiguous."
		),
		instruction=_PROMPT.read_text(encoding="utf-8"),
		mode="single_turn",
		before_model_callback=isolate_current_turn,
	)
