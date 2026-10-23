from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from qdrant_client.models import PointIdsList

from agents.tools.functions.ingest import documents


class _Point:
    def __init__(self, point_id: str) -> None:
        self.id = point_id


class _FakeQdrant:
    def __init__(self, ids: list[str]) -> None:
        self.ids = ids
        self.deleted: list[Any] | None = None

    def scroll(self, **_):
        return [_Point(point_id) for point_id in self.ids], None

    def delete(self, points_selector, **_):
        # Production passes a PointIdsList; record the ids it wraps.
        self.deleted = points_selector.points if isinstance(points_selector, PointIdsList) else points_selector


def _use_fake_qdrant(monkeypatch, fake: _FakeQdrant) -> None:
    monkeypatch.setattr(documents, "client", lambda: fake)
    monkeypatch.setattr(documents, "settings", lambda: SimpleNamespace(collection="test"))


def test_reingest_deletes_points_missing_from_new_version(monkeypatch) -> None:
    fake = _FakeQdrant(["old-1", "new-1"])
    _use_fake_qdrant(monkeypatch, fake)

    assert documents._delete_points_outside("src", "path", {"new-1"}) == 1
    assert fake.deleted == ["old-1"]


def test_ingest_texts_replaces_previous_chunks(monkeypatch) -> None:
    new_id = documents._point_id("src", 0, "new text")
    fake = _FakeQdrant(["old-chunk", new_id])
    _use_fake_qdrant(monkeypatch, fake)
    monkeypatch.setattr(documents, "ensure_collection", lambda: "test")
    monkeypatch.setattr(documents, "embed_texts", lambda texts: [[1.0, 0.0] for _ in texts])
    monkeypatch.setattr(documents, "upsert_points", lambda points: {"upserted": len(points)})

    result = documents.ingest_texts(["new text"], "src", {"file_path": "path"})

    assert result["replaced"] == 1
    assert fake.deleted == ["old-chunk"]


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


def test_eval_dataset_is_rejected_before_embedding(tmp_path, monkeypatch) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text(
        "id,question,reference_answer,expected_keywords\ncase-1,What is MFA?,A second factor.,factor\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(documents, "embed_texts", lambda _: pytest.fail("embedding must not run"))

    with pytest.raises(ValueError, match="evaluation dataset"):
        documents.ingest_file_to_qdrant(str(dataset))


def test_qa_csv_is_not_mistaken_for_eval_dataset() -> None:
    assert not documents._is_eval_csv("Question,Answer\nWhat is MFA?,A second factor.\n")


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
