from __future__ import annotations

from agents.tools.functions.ingest import documents


def test_csv_units_keep_complete_rows() -> None:
    text = "name,age\nAlice,25\nMissing\nBob,30,extra"
    assert documents._structure_units(text, ".csv") == ["name: Alice, age: 25"]


def test_qa_csv_records_keep_each_question_with_its_answer() -> None:
    text = (
        "Question,Answer,Category,Difficulty\n"
        '"How do I respond?","Isolate the affected device, then restore from backups.",Incident Response,Basic\n'
        '"What is MFA?","A second verification factor.",Authentication,Basic\n'
    )

    records = documents._qa_csv_records(text)

    assert records is not None
    assert len(records) == 2
    assert records[0]["text"] == (
        "Question: How do I respond?\n"
        "Answer: Isolate the affected device, then restore from backups."
    )
    assert records[0]["category"] == "Incident Response"
    assert records[0]["difficulty"] == "Basic"


def test_hybrid_chunks_respect_maximum_size(monkeypatch) -> None:
    monkeypatch.setattr(documents, "embed_texts", lambda units: [[1.0, 0.0] for _ in units])
    chunks = documents.hybrid_chunk_text(
        "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
        chunk_size=24,
        overlap=4,
        suffix=".md",
    )
    assert chunks
    assert all(len(chunk) <= 24 for chunk in chunks)
