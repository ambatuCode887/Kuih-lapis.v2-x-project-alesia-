from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents.llm_agent import Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.utils.context_utils import Aclosing

from agents.config import agent_model
from agents.tools.agents.clarification_agents.agent import clarification_agent
from agents.tools.agents.verification_agents.agent import verification_agent

_ASSESSMENT_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_ASSESSMENT_AGENTS = {"message_agent", "url_check_agent"}
CONFIDENCE_THRESHOLD = 60


def select_follow_up_agent(assessment: dict[str, Any] | None) -> str:
	"""Select a follow-up deterministically, defaulting to clarification."""
	if not assessment:
		return "clarification_agent"
	if assessment.get("clarification_needed") is True:
		return "clarification_agent"
	if assessment.get("risk_level") == "insufficient_information":
		return "clarification_agent"

	confidence = assessment.get("confidence")
	if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
		return "clarification_agent"
	if not 0 <= confidence <= 100 or confidence < CONFIDENCE_THRESHOLD:
		return "clarification_agent"
	return "verification_agent"


def parse_assessment(text: str) -> dict[str, Any] | None:
	for match in reversed(list(_ASSESSMENT_BLOCK.finditer(text))):
		try:
			assessment = json.loads(match.group(1))
		except json.JSONDecodeError:
			continue
		if isinstance(assessment, dict) and "confidence" in assessment:
			return assessment

	start = text.find("{")
	if start >= 0:
		try:
			assessment, _ = json.JSONDecoder().raw_decode(text[start:])
		except json.JSONDecodeError:
			return None
		if isinstance(assessment, dict) and "confidence" in assessment:
			return assessment
	return None


def _assessment_from_context(ctx: InvocationContext) -> dict[str, Any] | None:
	for event in reversed(ctx.session.events):
		if (
			event.invocation_id != ctx.invocation_id
			or event.author not in _ASSESSMENT_AGENTS
			or not event.content
		):
			continue
		text = "\n".join(
			part.text
			for part in event.content.parts or []
			if getattr(part, "text", None)
		)
		assessment = parse_assessment(text)
		if assessment is not None:
			return assessment
	return None


class ConfidenceRouter(Agent):
	"""Route structured assessments without an LLM making the branch decision."""

	async def _run_async_impl(
		self, ctx: InvocationContext
	) -> AsyncGenerator[Event, None]:
		assessment = ctx.session.state.get("coordinator_assessment")
		if not isinstance(assessment, dict):
			assessment = _assessment_from_context(ctx)
		target_name = select_follow_up_agent(assessment)
		target = next(
			(agent for agent in self.sub_agents if agent.name == target_name),
			None,
		)
		if target is None:
			raise RuntimeError(f"Configured route is missing agent: {target_name}")

		async with Aclosing(target.run_async(ctx)) as events:
			async for event in events:
				yield event


def coordinator_agent() -> Agent:
	"""Create the deterministic confidence-based follow-up router."""
	return ConfidenceRouter(
		model=agent_model(),
		name="coordinator_agent",
		description=(
			"Routes assessments below the confidence threshold or with missing "
			"evidence to clarification; otherwise routes to verification."
		),
		sub_agents=[clarification_agent(), verification_agent()],
	)



