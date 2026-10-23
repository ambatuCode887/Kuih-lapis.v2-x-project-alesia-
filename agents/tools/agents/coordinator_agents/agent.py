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


def _is_number(value: Any) -> bool:
	return isinstance(value, (int, float)) and not isinstance(value, bool)


def _risk_level(score: int | None) -> str:
	if score is None:
		return "insufficient_information"
	if score >= 75:
		return "critical"
	if score >= 50:
		return "high"
	if score >= 25:
		return "moderate"
	return "low"


def merge_assessments(assessments: list[dict[str, Any]]) -> dict[str, Any]:
	"""Combine channel assessments: the highest score is kept and the lowest confidence gates routing."""
	scores = [a["risk_score"] for a in assessments if _is_number(a.get("risk_score"))]
	score = max(scores) if scores else None
	confidences = [
		a["confidence"] if _is_number(a.get("confidence")) else 0 for a in assessments
	]
	actions: list[str] = []
	for assessment in assessments:
		for action in assessment.get("recommended_actions") or []:
			if isinstance(action, str) and action not in actions:
				actions.append(action)
	return {
		"risk_score": score,
		"risk_level": _risk_level(score),
		"confidence": min(confidences) if confidences else 0,
		"indicators": [
			indicator
			for assessment in assessments
			for indicator in assessment.get("indicators") or []
			if isinstance(indicator, dict)
		],
		"assessment": " ".join(
			a["assessment"].strip()
			for a in assessments
			if isinstance(a.get("assessment"), str) and a["assessment"].strip()
		),
		"recommended_actions": actions,
	}


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
		text = "\n".join(part.text for part in event.content.parts or [] if part.text)
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
		disallow_transfer_to_parent=True,
		disallow_transfer_to_peers=True,
		sub_agents=[clarification_agent(), verification_agent()],
	)



