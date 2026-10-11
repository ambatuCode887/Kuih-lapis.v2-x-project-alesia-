from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvaluationCase:
	case_id: str
	question: str
	reference_answer: str
	expected_keywords: tuple[str, ...]


def default_dataset_path() -> Path:
	return Path(__file__).resolve().parents[1] / "tools" / "knowledge" / "dataset.csv"


def default_ragas_dataset_path() -> Path:
	return (
		Path(__file__).resolve().parents[1]
		/ "tools"
		/ "knowledge"
		/ "navigator-batch-generate-66e2f34668701698ce0e0df3-data.csv"
	)


def load_cases(path: str | Path | None = None) -> list[EvaluationCase]:
	"""Load retrieval evaluation cases from a CSV file."""
	dataset_path = Path(path) if path else default_dataset_path()
	if not dataset_path.exists():
		raise FileNotFoundError(f"Evaluation dataset not found: {dataset_path}")

	with dataset_path.open(newline="", encoding="utf-8-sig") as handle:
		reader = csv.DictReader(handle)
		required = {"id", "question", "reference_answer", "expected_keywords"}
		missing = required - set(reader.fieldnames or [])
		if missing:
			raise ValueError(f"Dataset is missing columns: {', '.join(sorted(missing))}")

		cases = []
		for row in reader:
			question = (row.get("question") or "").strip()
			if not question:
				continue
			keywords = tuple(
				item.strip().lower()
				for item in (row.get("expected_keywords") or "").split("|")
				if item.strip()
			)
			cases.append(
				EvaluationCase(
					case_id=(row.get("id") or str(len(cases) + 1)).strip(),
					question=question,
					reference_answer=(row.get("reference_answer") or "").strip(),
					expected_keywords=keywords,
				)
			)
		return cases


def load_ragas_cases(path: str | Path | None = None) -> list[EvaluationCase]:
	"""Load question/reference-answer pairs from a knowledge or eval CSV."""
	dataset_path = Path(path) if path else default_ragas_dataset_path()
	if not dataset_path.exists():
		raise FileNotFoundError(f"RAGAS dataset not found: {dataset_path}")

	with dataset_path.open(newline="", encoding="utf-8-sig") as handle:
		reader = csv.DictReader(handle)
		fields = {
			field.strip().casefold(): field
			for field in (reader.fieldnames or [])
			if field
		}
		question_field = fields.get("question")
		answer_field = fields.get("answer") or fields.get("reference_answer")
		if question_field is None or answer_field is None:
			raise ValueError("RAGAS dataset must contain question and answer/reference_answer columns.")

		id_field = fields.get("id")
		keywords_field = fields.get("expected_keywords")
		cases = []
		for row in reader:
			question = (row.get(question_field) or "").strip()
			reference_answer = (row.get(answer_field) or "").strip()
			if not question or not reference_answer:
				continue
			keywords = tuple(
				item.strip().lower()
				for item in (row.get(keywords_field) or "").split("|")
				if item.strip()
			) if keywords_field else ()
			cases.append(
				EvaluationCase(
					case_id=(row.get(id_field) or str(len(cases) + 1)).strip()
					if id_field
					else str(len(cases) + 1),
					question=question,
					reference_answer=reference_answer,
					expected_keywords=keywords,
				)
			)
		return cases
