from __future__ import annotations

from agents.eval.dataset import EvaluationCase, load_cases, load_ragas_cases
from agents.eval.ragas_runner import (
    _source_grounding_result,
    evaluate_retrieval,
)


def test_load_cases(tmp_path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text(
        "id,question,reference_answer,expected_keywords\n"
        "one,What is RAG?,A retrieval system.,retrieval|generation\n",
        encoding="utf-8",
    )
    cases = load_cases(dataset)
    assert cases[0].case_id == "one"
    assert cases[0].expected_keywords == ("retrieval", "generation")


def test_load_ragas_cases_supports_knowledge_qa_csv(tmp_path) -> None:
    dataset = tmp_path / "knowledge.csv"
    dataset.write_text(
        "Question,Answer,Category,Difficulty\n"
        '"What is RAG?","Retrieval augmented generation.",AI,Basic\n',
        encoding="utf-8",
    )

    cases = load_ragas_cases(dataset)

    assert cases[0].question == "What is RAG?"
    assert cases[0].reference_answer == "Retrieval augmented generation."


def test_evaluate_retrieval_reports_keyword_recall() -> None:
    report = evaluate_retrieval(
        [EvaluationCase("one", "Question", "Answer", ("alpha", "beta"))],
        lambda question, limit=5: {"results": [{"text": "Alpha is present."}]},
    )
    assert report["average_keyword_recall"] == 0.5


def test_retrieve_knowledge_normalizes_null_score_threshold(monkeypatch) -> None:
    from agents.tools.functions.retrieve import credential_stuffing

    captured = {}
    monkeypatch.setattr(credential_stuffing, "embed_text", lambda query: [0.1])
    monkeypatch.setattr(
        credential_stuffing,
        "search",
        lambda **kwargs: captured.update(kwargs) or [],
    )

    credential_stuffing.retrieve_knowledge("phishing URL", score_threshold="none")

    assert captured["score_threshold"] is None


def test_source_grounding_requires_a_retrieved_citation() -> None:
    valid = _source_grounding_result(
        "Use MFA [data.md#1]", ["[data.md#1]"]
    )
    invalid = _source_grounding_result(
        "Use MFA [other.md#1]", ["[data.md#1]"]
    )

    assert valid["has_valid_source_citation"] is True
    assert valid["invalid_or_unretrieved_citations"] == []
    assert invalid["has_valid_source_citation"] is False
    assert invalid["invalid_or_unretrieved_citations"] == ["[other.md#1]"]


def test_heldout_questions_are_separate_from_indexed_and_development_questions() -> None:
    from pathlib import Path

    from agents.eval.dataset import default_ragas_dataset_path, load_ragas_cases

    eval_datasets_dir = (
        Path(__file__).resolve().parents[1]
        / "agents"
        / "eval"
        / "datasets"
    )
    heldout_path = eval_datasets_dir / "heldout_cybersecurity.csv"
    heldout = load_ragas_cases(heldout_path)
    indexed = load_ragas_cases(default_ragas_dataset_path())
    dev = load_ragas_cases(eval_datasets_dir / "retrieval_dev_cybersecurity.csv")
    other_questions = {case.question.strip().casefold() for case in [*indexed, *dev]}

    assert len(heldout) == 8
    assert all(case.expected_keywords for case in load_cases(heldout_path))
    assert all(case.question.strip().casefold() not in other_questions for case in heldout)