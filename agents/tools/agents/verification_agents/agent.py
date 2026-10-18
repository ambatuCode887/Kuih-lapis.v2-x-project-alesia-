from pathlib import Path
from typing import Any

from google.adk.agents.llm_agent import Agent

from agents.config import agent_model
from agents.tools.agents.message_agents.attachments import isolate_current_turn
from agents.tools.functions.retrieve.credential_stuffing import (
	DEFAULT_SCORE_THRESHOLD,
	retrieve_knowledge,
)


_PROMPT = Path(__file__).parent / "prompt.md"
_EVIDENCE_RULES = """

Treat the current message or OCR text as the evidence. Preserve its exact
meaning: a password request is not a one-time or verification-code request.
Only include a retrieved passage when it directly supports a claim about that
evidence. If no sufficiently relevant passage is returned, say that the
knowledge base had no relevant match and do not fill the gap with unrelated
topics or generic procedural advice. Keep the explanation consistent with the
specialist assessment and quote the message when identifying a warning sign.
"""


def retrieve_verification_knowledge(query: str) -> dict[str, Any]:
	"""Retrieve only high-relevance evidence for scam verification."""
	return retrieve_knowledge(
		query=query,
		limit=3,
		score_threshold=DEFAULT_SCORE_THRESHOLD,
	)


def verification_agent() -> Agent:
	"""Create the sub-agent for scam-pattern retrieval and verification guidance."""
	return Agent(
		model=agent_model(),
		name="verification_agent",
		description=(
			"Checks supplied scam indicators against the internal knowledge base "
			"and guides users through independent official verification."
		),
		instruction=_PROMPT.read_text(encoding="utf-8") + _EVIDENCE_RULES,
		tools=[retrieve_verification_knowledge],
		mode="single_turn",
		disallow_transfer_to_parent=True,
		disallow_transfer_to_peers=True,
		before_model_callback=isolate_current_turn,
	)
