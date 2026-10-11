from pathlib import Path

from google.adk.agents.llm_agent import Agent

from agents.config import agent_model

from agents.tools.functions.classify import classify_precomputed_features


_PROMPT = Path(__file__).parent / "prompt.md"


def file_classifier_agent() -> Agent:
	"""Create the sub-agent for scoring pre-extracted file features."""
	return Agent(
		model=agent_model(),
		name="file_classifier_agent",
		description=(
			"Scores complete, pre-extracted feature vectors with local "
			"Excel, HTML, PDF, or Word classifiers."
		),
		instruction=_PROMPT.read_text(encoding="utf-8"),
		tools=[classify_precomputed_features],
		mode="single_turn",
	)