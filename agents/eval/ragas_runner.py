from __future__ import annotations

import json
from collections.abc import Callable
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
) -> dict[str, Any]:
	"""Score generated answers against retrieved context and reference answers."""
	from datasets import Dataset
	from ragas import evaluate
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
	for case in cases:
		retrieved = retrieve(case.question, limit=limit)
		contexts = [
			item.get("text", "")
			for item in retrieved.get("results", [])
			if item.get("text")
		]
		samples.append(
			{
				"user_input": case.question,
				"response": generate_answer(case.question, contexts),
				"retrieved_contexts": contexts,
				"reference": case.reference_answer,
			}
		)

	metrics = [
		Faithfulness(llm=llm),
		AnswerRelevancy(llm=llm, embeddings=_RagasEmbeddingAdapter(embeddings)),
		ContextRecall(llm=llm),
		ContextPrecision(llm=llm),
		AnswerCorrectness(llm=llm, embeddings=_RagasEmbeddingAdapter(embeddings)),
	]
	result = evaluate(
		dataset=Dataset.from_list(samples),
		metrics=metrics,
		llm=llm,
		embeddings=embeddings,
		run_config=RunConfig(timeout=240, max_retries=2, max_workers=1),
		raise_exceptions=True,
		show_progress=True,
	)
	scores = result.to_pandas()
	metric_names = [metric.name for metric in metrics]
	averages = {
		name: float(scores[name].dropna().mean())
		for name in metric_names
		if name in scores and not scores[name].dropna().empty
	}
	return {
		"evaluation": "RAGAS",
		"case_count": len(samples),
		"metrics": averages,
		"cases": json.loads(scores.to_json(orient="records", force_ascii=False)),
	}
