from pathlib import Path

from google.adk.agents.llm_agent import Agent

from agents.config import agent_model
from agents.tools.agents.message_agents.attachments import prepare_message_attachments


_PROMPT = Path(__file__).parent / "prompt.md"
_EVIDENCE_RULES = """

For image or document checks, base every claim on readable extracted text or
clearly visible evidence. Quote the exact short phrase supporting each
indicator. Keep password requests distinct from one-time codes or verification
codes; do not substitute one for the other. Do not add unrelated guidance
(such as software-update or certificate advice) unless the evidence calls for
it. If the text is incomplete or ambiguous, say what is unclear, lower
confidence, and keep the assessment and explanation consistent.
"""


def message_agent() -> Agent:
	"""Create the sub-agent for analyzing suspicious messages."""
	return Agent(
		model=agent_model(),
		name="message_agent",
		description=(
			"Analyzes user-provided messages for scam and spam indicators, "
			"with evidence-based risk guidance."
		),
		instruction=_PROMPT.read_text(encoding="utf-8") + _EVIDENCE_RULES,
		mode="single_turn",
		disallow_transfer_to_parent=True,
		disallow_transfer_to_peers=True,
		before_model_callback=prepare_message_attachments,
	)
