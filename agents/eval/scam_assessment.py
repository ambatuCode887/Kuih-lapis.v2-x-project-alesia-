from __future__ import annotations

import argparse
import asyncio
import csv
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.config import env, load_environment
from agents.tools.agents.coordinator_agents.agent import (
	parse_assessment,
	select_follow_up_agent,
)
from agents.tools.agents.message_agents.agent import message_agent

_DATASET_PATH = Path(__file__).with_name("scam_assessment_cases.csv")
_DEFAULT_OUTPUT = Path(".artifacts/scam-assessment-report.json")
_RISK_LEVELS = {"low", "moderate", "high", "critical", "insufficient_information"}
_INDICATOR_TYPES = {
	"urgency",
	"impersonation",
	"credential_request",
	"payment_request",
	"secrecy",
	"suspicious_link",
	"other",
}
_ASSESSMENT_KEYS = {
	"risk_score",
	"risk_level",
	"confidence",
	"indicators",
	"assessment",
	"recommended_actions",
}


def load_reviewed_cases(path: str | Path = _DATASET_PATH) -> list[dict[str, str]]:
	with Path(path).open(newline="", encoding="utf-8") as handle:
		cases = list(csv.DictReader(handle))
	if not cases:
		raise ValueError("The scam-assessment dataset contains no cases.")
	if any(case.get("review_status") != "reviewed" for case in cases):
		raise ValueError("Every case must be reviewed before model evaluation.")
	return cases


def validate_assessment(assessment: dict[str, Any]) -> dict[str, list[str]]:
	schema_errors = []
	consistency_errors = []
	if set(assessment) != _ASSESSMENT_KEYS:
		schema_errors.append("top-level keys do not match the required schema")

	risk_level = assessment.get("risk_level")
	if risk_level not in _RISK_LEVELS:
		schema_errors.append("risk_level is invalid")

	risk_score = assessment.get("risk_score")
	if risk_score is not None and (
		isinstance(risk_score, bool)
		or not isinstance(risk_score, int)
		or not 0 <= risk_score <= 100
	):
		schema_errors.append("risk_score must be null or an integer from 0 to 100")
	elif risk_score is None and risk_level != "insufficient_information":
		consistency_errors.append(
			"a null risk_score requires insufficient_information risk_level"
		)
	elif risk_score is not None:
		expected_level = (
			"low" if risk_score < 25 else
			"moderate" if risk_score < 50 else
			"high" if risk_score < 75 else
			"critical"
		)
		if risk_level != expected_level:
			consistency_errors.append(
				"risk_score does not match the documented risk_level band"
			)

	confidence = assessment.get("confidence")
	if (
		isinstance(confidence, bool)
		or not isinstance(confidence, int)
		or not 0 <= confidence <= 100
	):
		schema_errors.append("confidence must be an integer from 0 to 100")

	indicators = assessment.get("indicators")
	if not isinstance(indicators, list):
		schema_errors.append("indicators must be a list")
	else:
		for index, indicator in enumerate(indicators):
			if not isinstance(indicator, dict):
				schema_errors.append(f"indicator {index} must be an object")
				continue
			if set(indicator) != {"type", "evidence", "reason"}:
				schema_errors.append(f"indicator {index} has unexpected or missing fields")
			if indicator.get("type") not in _INDICATOR_TYPES:
				schema_errors.append(f"indicator {index} has an invalid type")
			if not isinstance(indicator.get("evidence"), str) or not isinstance(
				indicator.get("reason"), str
			):
					schema_errors.append(
						f"indicator {index} must include evidence and reason text"
					)

	if not isinstance(assessment.get("assessment"), str):
			schema_errors.append("assessment must be a string")
	if not isinstance(assessment.get("recommended_actions"), list) or not all(
		isinstance(action, str) for action in assessment.get("recommended_actions", [])
	):
		schema_errors.append("recommended_actions must be a list of strings")
	return {
		"schema_errors": schema_errors,
		"consistency_errors": consistency_errors,
	}


def score_result(
	case: dict[str, str],
	assessment: dict[str, Any] | None,
	response_text: str,
	parse_error: str | None = None,
) -> dict[str, Any]:
	if assessment is None:
		return {
			"case_id": case["case_id"],
			"schema_valid": False,
			"schema_errors": [parse_error or "assessment JSON was not found"],
			"consistency_errors": [],
			"response_text": response_text,
		}

	validation = validate_assessment(assessment)
	schema_errors = validation["schema_errors"]
	consistency_errors = validation["consistency_errors"]
	actual_indicators = {
		item.get("type")
		for item in assessment.get("indicators", [])
		if isinstance(item, dict) and isinstance(item.get("type"), str)
	}
	expected_indicators = {
		item for item in case["expected_indicators"].split("|") if item
	}
	indicator_recall = (
		sum(item in actual_indicators for item in expected_indicators)
		/ len(expected_indicators)
		if expected_indicators
		else None
	)
	clarification_expected = case["clarification_expected"].casefold() == "true"
	clarification_actual = (
		select_follow_up_agent(assessment) == "clarification_agent"
	)

	return {
		"case_id": case["case_id"],
		"schema_valid": not schema_errors,
		"schema_errors": schema_errors,
		"score_consistent": not consistency_errors,
		"consistency_errors": consistency_errors,
		"expected_risk_level": case["expected_risk_level"],
		"actual_risk_level": assessment.get("risk_level"),
		"risk_level_match": assessment.get("risk_level") == case["expected_risk_level"],
		"expected_indicators": sorted(expected_indicators),
		"actual_indicators": sorted(actual_indicators),
		"expected_indicator_recall": indicator_recall,
		"unexpected_indicators": sorted(actual_indicators - expected_indicators),
		"expected_clarification": clarification_expected,
		"actual_clarification": clarification_actual,
		"clarification_match": clarification_actual == clarification_expected,
		"assessment": assessment,
		"response_text": response_text,
	}


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
	count = len(results)
	if not count:
		return {"case_count": 0}

	valid_count = sum(result.get("schema_valid", False) for result in results)
	consistent_count = sum(result.get("score_consistent", False) for result in results)
	parsed = [result for result in results if "risk_level_match" in result]
	with_indicator_targets = [
		result
		for result in results
		if result.get("expected_indicator_recall") is not None
	]
	return {
		"case_count": count,
		"valid_schema_rate": valid_count / count,
		"score_consistency_rate": consistent_count / count,
		"risk_level_exact_match_rate": (
			sum(result["risk_level_match"] for result in parsed) / len(parsed)
			if parsed
			else None
		),
		"clarification_routing_match_rate": (
			sum(result["clarification_match"] for result in parsed) / len(parsed)
			if parsed
			else None
		),
		"mean_expected_indicator_recall": (
			sum(result["expected_indicator_recall"] for result in with_indicator_targets)
			/ len(with_indicator_targets)
			if with_indicator_targets
			else None
		),
		"cases_with_expected_indicators": len(with_indicator_targets),
	}


async def _collect_response_events(
	runner: Runner,
	user_id: str,
	session_id: str,
	user_request: str,
) -> list[Any]:
	return [
		event
		async for event in runner.run_async(
			user_id=user_id,
			session_id=session_id,
			new_message=types.Content(
				role="user",
				parts=[types.Part(text=user_request)],
			),
		)
	]


async def _evaluate_cases(
	cases: list[dict[str, str]],
	timeout_seconds: float = 180,
	checkpoint: Callable[[list[dict[str, Any]]], None] | None = None,
) -> list[dict[str, Any]]:
	app_name = "scam_assessment_eval"
	user_id = "scam_assessment_eval"
	session_service = InMemorySessionService()
	root = SequentialAgent(
		name="scam_assessment_eval_root",
		description="Runs the message assessment specialist without other agents.",
		sub_agents=[message_agent()],
	)
	runner = Runner(
		app_name=app_name,
		agent=root,
		session_service=session_service,
	)
	results = []
	for index, case in enumerate(cases, start=1):
		try:
			session = await session_service.create_session(
				app_name=app_name,
				user_id=user_id,
			)
			response_events = await asyncio.wait_for(
				_collect_response_events(
					runner,
					user_id,
					session.id,
					case["user_request"],
				),
				timeout=timeout_seconds,
			)
			message_events = [
				event
				for event in response_events
				if event.author == "message_agent" and event.content
			]
			response_text = "\n".join(
				part.text
				for part in (message_events[-1].content.parts if message_events else [])
				if getattr(part, "text", None)
			)
			assessment = parse_assessment(response_text) if response_text else None
			result = score_result(
				case,
				assessment,
				response_text,
				parse_error="no message_agent assessment event was returned"
				if not message_events
				else None,
			)
		except asyncio.TimeoutError:
			result = {
				"case_id": case["case_id"],
				"schema_valid": False,
				"schema_errors": [],
				"consistency_errors": [],
				"inference_error": f"model call timed out after {timeout_seconds:g} seconds",
			}
		except Exception as error:
			result = {
				"case_id": case["case_id"],
				"schema_valid": False,
				"schema_errors": [],
				"consistency_errors": [],
				"inference_error": f"{type(error).__name__}: {error}",
			}
		results.append(result)
		status = (
			f"error: {result['inference_error']}"
			if "inference_error" in result
			else f"schema_valid={result['schema_valid']}, "
				 f"risk_match={result.get('risk_level_match')}, "
				 f"clarification_match={result.get('clarification_match')}"
		)
		print(f"[{index}/{len(cases)}] {case['case_id']}: {status}", flush=True)
		if checkpoint:
			checkpoint(results)
	return results


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Evaluate message_agent against reviewed scam-assessment cases."
	)
	parser.add_argument("--dataset", default=str(_DATASET_PATH))
	parser.add_argument("--output", default=str(_DEFAULT_OUTPUT))
	parser.add_argument("--limit", type=int, default=0, help="Maximum cases; 0 runs all")
	parser.add_argument(
		"--timeout",
		type=float,
		default=180,
		help="Per-case model timeout in seconds (default: 180)",
	)
	args = parser.parse_args()
	if args.limit < 0:
		parser.error("--limit must be non-negative")
	if args.timeout <= 0:
		parser.error("--timeout must be greater than zero")

	try:
		cases = load_reviewed_cases(args.dataset)
	except (OSError, ValueError) as error:
		parser.error(str(error))
	if args.limit:
		cases = cases[: args.limit]

	load_environment()
	model_name = env("OLLAMA_MODEL", "qwen2.5:7b") or "qwen2.5:7b"
	output_path = Path(args.output)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	results: list[dict[str, Any]] = []

	def write_checkpoint(current_results: list[dict[str, Any]]) -> None:
		report = {
			"model": model_name,
			"dataset": str(Path(args.dataset).resolve()),
			"completed_case_count": len(current_results),
			"requested_case_count": len(cases),
			"complete": len(current_results) == len(cases),
			"note": (
				"Scores compare model outputs with reviewed heuristic expectations. "
				"Risk scores are not calibrated probabilities; manually inspect each case."
			),
			"summary": summarize_results(current_results),
			"cases": current_results,
		}
		output_path.write_text(
			json.dumps(report, indent=2, ensure_ascii=False),
			encoding="utf-8",
		)

	results = asyncio.run(
		_evaluate_cases(cases, timeout_seconds=args.timeout, checkpoint=write_checkpoint)
	)
	write_checkpoint(results)
	print(json.dumps(summarize_results(results), indent=2))
	print(f"Detailed report: {output_path.resolve()}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())