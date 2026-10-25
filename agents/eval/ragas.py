"""Run the local retrieval evaluation suite against Qdrant."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from typing import Any
from pathlib import Path

from openai import OpenAI
from ragas.embeddings.base import BaseRagasEmbedding

from agents.config import env
from agents.eval.dataset import default_dataset_path, default_ragas_dataset_path, load_cases, load_ragas_cases
from agents.eval.ragas_runner import evaluate_ragas, evaluate_retrieval
from agents.tools.functions.embeddings import embed_texts as configured_embed_texts
from agents.tools.functions.retrieve.credential_stuffing import retrieve_knowledge


class _ConfiguredRagasEmbedding(BaseRagasEmbedding):
	"""Expose the app's configured embedding provider through RAGAS's interface."""

	def embed_text(self, text: str, **kwargs: Any) -> list[float]:
		return configured_embed_texts([text])[0]

	def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
		return configured_embed_texts(texts)

	async def aembed_text(self, text: str, **kwargs: Any) -> list[float]:
		return await asyncio.to_thread(self.embed_text, text)

	async def aembed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
		return await asyncio.to_thread(self.embed_texts, texts)


def main() -> int:
	parser = argparse.ArgumentParser(description="Run RAGAS evaluation against Qdrant")
	parser.add_argument("--dataset", help="Q&A CSV; defaults to the newly ingested knowledge CSV")
	parser.add_argument("--output", help="Path for the JSON report")
	parser.add_argument("--limit", type=int, default=10, help="Sample size; use 0 to evaluate every row")
	parser.add_argument("--seed", type=int, default=42, help="Seed for repeatable sampling")
	parser.add_argument("--top-k", type=int, default=5, help="Retrieved contexts per question")
	parser.add_argument("--keyword-only", action="store_true", help="Run the lightweight keyword-recall baseline")
	parser.add_argument(
		"--grounding-only",
		action="store_true",
		help="Generate answers and audit their citations without running RAGAS judge metrics",
	)
	args = parser.parse_args()
	if args.keyword_only and args.grounding_only:
		parser.error("--keyword-only and --grounding-only cannot be used together")

	if args.keyword_only:
		cases = load_cases(args.dataset or default_dataset_path())
		if not cases:
			print("No evaluation cases found. Add rows to agents/tools/knowledge/dataset.csv.")
			return 1
		report = evaluate_retrieval(cases, retrieve_knowledge)
		default_output = ".artifacts/retrieval-report.json"
	else:
		if args.limit < 0 or args.top_k < 1:
			parser.error("--limit must be non-negative and --top-k must be at least 1")
		cases = load_ragas_cases(args.dataset or default_ragas_dataset_path())
		if not cases:
			print("No question/reference-answer rows found in the dataset.")
			return 1
		if args.limit and len(cases) > args.limit:
			cases = random.Random(args.seed).sample(cases, args.limit)

		base_url = (env("OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434").rstrip("/")
		model = env("OLLAMA_MODEL", "qwen2.5:7b") or "qwen2.5:7b"
		embedding_provider = (env("EMBEDDING_PROVIDER", "google") or "google").strip().lower()
		default_embedding_model = (
			"nomic-embed-text:latest" if embedding_provider == "ollama" else "gemini-embedding-001"
		)
		embedding_model = env("EMBEDDING_MODEL", default_embedding_model) or default_embedding_model
		client = OpenAI(base_url=f"{base_url}/v1", api_key="ollama", timeout=240)
		from ragas.llms import llm_factory

		llm = llm_factory(model=model, client=client)
		embeddings = _ConfiguredRagasEmbedding()

		def generate_answer(question: str, contexts: list[str]) -> str:
			context_text = "\n\n".join(contexts) or "No relevant context was retrieved."
			response = client.chat.completions.create(
				model=model,
				messages=[
					{
						"role": "system",
						"content": (
							"Answer using only the retrieved context. Cite factual claims using "
							"the exact source token shown before each passage, such as "
							"[data.md#2]. Never invent a citation. If retrieved context does "
							"not support an answer, say that the knowledge base did not provide one."
						),
					},
					{
						"role": "user",
						"content": f"Question:\n{question}\n\nRetrieved context:\n{context_text}",
					},
				],
				temperature=0,
				max_tokens=500,
			)
			return (response.choices[0].message.content or "").strip()

		report = evaluate_ragas(
			cases,
			retrieve_knowledge,
			generate_answer,
			llm,
			embeddings,
			limit=args.top_k,
			grounding_only=args.grounding_only,
		)
		report["dataset"] = str(Path(args.dataset or default_ragas_dataset_path()).resolve())
		report["sample_seed"] = args.seed
		report["sample_limit"] = args.limit or "all"
		report["answer_model"] = model
		report["embedding_provider"] = embedding_provider
		report["embedding_model"] = embedding_model
		if not args.grounding_only:
			report["judge_model"] = model
		report["evaluation_note"] = (
			"This evaluation uses a caller-supplied dataset. Treat it as held out only "
			"if its questions were not used to build or tune the indexed corpus."
			if args.dataset
			else "This in-sample check uses questions from the indexed knowledge CSV; "
			"use a separate held-out Q&A file to estimate generalization."
		)
		default_output = ".artifacts/ragas-report.json"

	output = Path(args.output or default_output)
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
	print(json.dumps(report, indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

