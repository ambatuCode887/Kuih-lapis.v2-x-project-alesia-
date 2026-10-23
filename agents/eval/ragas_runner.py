from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agents.eval.dataset import EvaluationCase


class _RagasEmbeddingAdapter:
	def __init__(self, embeddings: Any) -> None:
		self.embeddings = embeddings

	async def embed_text(self, text: str) -> list[float]:
		return self.embeddings.embed_text(text)

	def embed_query(self, text: str) -> list[float]:
		return self.embeddings.embed_text(text)

	def embed_documents(self, texts: list[str]) -> list[list[float]]:
		return self.embeddings.embed_texts(texts)


def _format_retrieved_context(item: dict[str, Any]) -> tuple[str, str | None]:
	text = str(item.get("text", ""))
	source = str(item.get("source", ""))
	chunk_index = item.get("chunk_index")
	if not source or chunk_index is None:
		return text, None
	citation = f"[{Path(source).name}#{chunk_index}]"
	return f"{citation}\n{text}", citation


def _source_grounding_result(
	response: str,
	retrieved_citations: list[str],
) -> dict[str, Any]:
	answer_citations = [
		f"[{citation}]"
		for citation in re.findall(r"\[([^\]]+#[^\]]+)\]", response)
	]
	valid_citations = sorted(set(answer_citations) & set(retrieved_citations))
	invalid_citations = sorted(set(answer_citations) - set(retrieved_citations))
	return {
		"retrieved_source_citations": retrieved_citations,
		"answer_source_citations": sorted(set(answer_citations)),
		"valid_retrieved_citations": valid_citations,
		"invalid_or_unretrieved_citations": invalid_citations,
		"has_valid_source_citation": bool(valid_citations),
		"all_answer_citations_retrieved": bool(answer_citations) and not invalid_citations,
	}


def evaluate_retrieval(
	cases: list[EvaluationCase],
	retrieve: Callable[..., dict[str, Any]],
	limit: int = 5,
) -> dict[str, Any]:
	"""Evaluate whether retrieved context contains each case's expected keywords."""
	results = []
	for case in cases:
		response = retrieve(case.question, limit=limit)
		context = " ".join(item.get("text", "") for item in response.get("results", [])).lower()
		matched = [keyword for keyword in case.expected_keywords if keyword in context]
		recall = len(matched) / len(case.expected_keywords) if case.expected_keywords else 0.0
		results.append(
			{
				"id": case.case_id,
				"question": case.question,
				"matched_keywords": matched,
				"keyword_recall": recall,
				"retrieved_count": len(response.get("results", [])),
			}
		)

	average = sum(item["keyword_recall"] for item in results) / len(results) if results else 0.0
	return {"case_count": len(results), "average_keyword_recall": average, "cases": results}


def evaluate_ragas(
	cases: list[EvaluationCase],
	retrieve: Callable[..., dict[str, Any]],
	generate_answer: Callable[[str, list[str]], str],
	llm: Any,
	embeddings: Any,
	limit: int = 5,
	grounding_only: bool = False,
) -> dict[str, Any]:
	"""Score generated answers against retrieved context and reference answers."""
	from datasets import Dataset
	from ragas import evaluate
	from ragas.dataset_schema import EvaluationResult
	from ragas.metrics import (
		AnswerCorrectness,
		AnswerRelevancy,
		ContextPrecision,
		ContextRecall,
		Faithfulness,
	)
	from ragas.run_config import RunConfig

	if not cases:
		raise ValueError("At least one evaluation case is required.")

	samples = []
	case_metadata = []
	for case in cases:
		retrieved = retrieve(case.question, limit=limit)
		contexts = []
		retrieved_sources = []
		retrieved_citations = []
		for item in retrieved.get("results", []):
			if not item.get("text"):
				continue
			context, citation = _format_retrieved_context(item)
			contexts.append(context)
			retrieved_sources.append(
				{
					"source": item.get("source", ""),
					"chunk_index": item.get("chunk_index"),
					"score": item.get("score"),
				}
			)
			if citation:
				retrieved_citations.append(citation)
		case_metadata.append(
			{
				"case_id": case.case_id,
				"question": case.question,
				"reference_answer": case.reference_answer,
				"retrieved_sources": retrieved_sources,
			}
		)
		samples.append(
			{
				"user_input": case.question,
				"response": generate_answer(case.question, contexts),
				"retrieved_contexts": contexts,
				"reference": case.reference_answer,
			}
		)
	if grounding_only:
		case_results = []
		for metadata, sample in zip(case_metadata, samples):
			retrieved_citations = [
				citation
				for context in sample["retrieved_contexts"]
				for citation in re.findall(r"^(\[[^\]]+#[^\]]+\])", context)
			]
			case_results.append(
				{
					**metadata,
					"response": sample["response"],
					**_source_grounding_result(
						sample["response"], retrieved_citations
					),
				}
			)
		citation_cases = [
			case for case in case_results if case["answer_source_citations"]
		]
		return {
			"evaluation": "source_citation_audit",
			"case_count": len(case_results),
			"metrics": {},
			"source_grounding": {
				"semantic_faithfulness_evaluated": False,
				"cases_with_retrieved_citations": sum(
					bool(case["retrieved_source_citations"]) for case in case_results
				),
				"cases_with_answer_citations": len(citation_cases),
				"all_citations_retrieved_rate": (
					sum(case["all_answer_citations_retrieved"] for case in citation_cases)
					/ len(citation_cases)
					if citation_cases
					else None
				),
				"cases_with_unretrieved_citations": sum(
					bool(case["invalid_or_unretrieved_citations"])
					for case in case_results
				),
			},
			"cases": case_results,
		}

	metrics = [Faithfulness(llm=llm)]
	if not grounding_only:
		metrics.extend(
			[
				AnswerRelevancy(llm=llm, embeddings=_RagasEmbeddingAdapter(embeddings)),
				ContextRecall(llm=llm),
				ContextPrecision(llm=llm),
				AnswerCorrectness(llm=llm, embeddings=_RagasEmbeddingAdapter(embeddings)),
			]
		)
	result = evaluate(
		dataset=Dataset.from_list(samples),
		metrics=metrics,
		llm=llm,
		embeddings=embeddings,
		run_config=RunConfig(timeout=240, max_retries=2, max_workers=1),
		raise_exceptions=True,
		show_progress=True,
	)
	if not isinstance(result, EvaluationResult):
		raise TypeError("ragas.evaluate returned an Executor instead of results.")
	scores = result.to_pandas()
	metric_names = [metric.name for metric in metrics]
	averages = {
		name: float(scores[name].dropna().mean())
		for name in metric_names
		if name in scores and not scores[name].dropna().empty
	}
	scores_json = scores.to_json(orient="records", force_ascii=False)
	if scores_json is None:
		raise ValueError("pandas returned no JSON for the RAGAS scores.")
	case_results = json.loads(scores_json)
	for case_result, metadata, sample in zip(case_results, case_metadata, samples):
		case_result.update(metadata)
		case_result.update(
			_source_grounding_result(
				sample["response"],
				[
					citation
					for context in sample["retrieved_contexts"]
					for citation in re.findall(r"^(\[[^\]]+#[^\]]+\])", context)
				],
			)
		)
	citation_cases = [
		case for case in case_results if case["retrieved_source_citations"]
	]
	return {
		"evaluation": "RAGAS",
		"evaluation_mode": "source_grounding" if grounding_only else "full_ragas",
		"case_count": len(samples),
		"metrics": averages,
		"source_grounding": {
			"cases_with_retrieved_citations": len(citation_cases),
			"valid_citation_rate": (
				sum(case["all_answer_citations_retrieved"] for case in citation_cases)
				/ len(citation_cases)
				if citation_cases
				else None
			),
			"cases_with_unretrieved_citations": sum(
				bool(case["invalid_or_unretrieved_citations"]) for case in case_results
			),
		},
		"cases": case_results,
	}
