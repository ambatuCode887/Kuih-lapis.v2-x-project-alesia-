"""Run the local retrieval evaluation suite against Qdrant."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from openai import OpenAI

from agents.config import env
from agents.eval.dataset import default_dataset_path, default_ragas_dataset_path, load_cases, load_ragas_cases
from agents.eval.ragas_runner import evaluate_ragas, evaluate_retrieval
from agents.tools.functions.retrieve.credential_stuffing import retrieve_knowledge


def main() -> int:
	parser = argparse.ArgumentParser(description="Run RAGAS evaluation against Qdrant")
	parser.add_argument("--dataset", help="Q&A CSV; defaults to the newly ingested knowledge CSV")
	parser.add_argument("--output", help="Path for the JSON report")
	parser.add_argument("--limit", type=int, default=10, help="Sample size; use 0 to evaluate every row")
	parser.add_argument("--seed", type=int, default=42, help="Seed for repeatable sampling")
	parser.add_argument("--top-k", type=int, default=5, help="Retrieved contexts per question")
	parser.add_argument("--keyword-only", action="store_true", help="Run the lightweight keyword-recall baseline")
	args = parser.parse_args()

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
		embedding_model = env("EMBEDDING_MODEL", "nomic-embed-text:latest") or "nomic-embed-text:latest"
		client = OpenAI(base_url=f"{base_url}/v1", api_key="ollama", timeout=240)
		from ragas.embeddings.base import embedding_factory
		from ragas.llms import llm_factory

		llm = llm_factory(model=model, client=client)
		embeddings = embedding_factory("openai", model=embedding_model, client=client)

		def generate_answer(question: str, contexts: list[str]) -> str:
			context_text = "\n\n".join(contexts) or "No relevant context was retrieved."
			response = client.chat.completions.create(
				model=model,
				messages=[
					{
						"role": "system",
						"content": (
							"Answer the user's question using only the retrieved context. "
							"If the context does not contain the answer, say so plainly."
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
		)
		report["dataset"] = str(Path(args.dataset or default_ragas_dataset_path()).resolve())
		report["sample_seed"] = args.seed
		report["sample_limit"] = args.limit or "all"
		report["judge_model"] = model
		report["embedding_model"] = embedding_model
		report["evaluation_note"] = (
			"This in-sample check uses questions from the indexed knowledge CSV; "
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

