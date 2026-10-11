from __future__ import annotations

from agents.eval.dataset import EvaluationCase, load_cases, load_ragas_cases
from agents.eval.ragas_runner import evaluate_retrieval


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