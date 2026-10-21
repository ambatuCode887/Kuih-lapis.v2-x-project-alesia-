from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.tools.functions.ingest import unanswered_sync as sync

HEADER = "timestamp_utc,question,model_answer,status\n"
APPROVED_ROW = '2026-10-20T13:04:52+00:00,What is MFA?,"A second verification factor.",approved_review\n'
PENDING_ROW = '2026-10-20T16:17:33+00:00,How do I secure Kubernetes?,"Draft text",pending_review\n'
DENIED_ROW = '2026-10-20T16:20:37+00:00,Who won the game?,"Unrelated",denied_review\n'


class FakeQdrant:
    def __init__(self) -> None:
        self.upserts: list = []
        self.deletes: list[str] = []
        self.stored: dict[str, str] = {}

    def scroll(self, *, collection_name, scroll_filter, limit, offset, with_payload, with_vectors):
        points = [SimpleNamespace(id=pid, payload={"text": text}) for pid, text in self.stored.items()]
        return points, None

    def upsert(self, *, collection_name, points, wait):
        self.upserts.extend(points)

    def delete(self, *, collection_name, points_selector, wait):
        self.deletes.extend(points_selector.points)


@pytest.fixture
def qdrant(monkeypatch) -> FakeQdrant:
    fake = FakeQdrant()
    monkeypatch.setattr(sync, "client", lambda: fake)
    monkeypatch.setattr(sync, "ensure_collection", lambda: "multi_agentic_rag")
    monkeypatch.setattr(sync, "settings", lambda: SimpleNamespace(collection="multi_agentic_rag"))
    monkeypatch.setattr(sync, "embed_texts", lambda texts: [[1.0, 0.0] for _ in texts])
    return fake


def write_log(tmp_path: Path, body: str, header: str = HEADER) -> Path:
    path = tmp_path / "unanswered_questions.csv"
    path.write_text(header + body, encoding="utf-8")
    return path


def test_only_approved_rows_are_upserted(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, APPROVED_ROW + PENDING_ROW + DENIED_ROW)

    summary = sync.sync_review_log(path)

    assert summary["upserted"] == 1
    [point] = qdrant.upserts
    assert point.payload["review_status"] == "approved_review"
    assert point.payload["text"] == "Question: What is MFA?\nAnswer: A second verification factor."
    assert qdrant.deletes == []


def test_dry_run_validates_without_writing(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, APPROVED_ROW + PENDING_ROW)

    summary = sync.sync_review_log(path, dry_run=True, prune=True)

    assert summary["approved"] == 1
    assert summary["would_prune"] == 1
    assert qdrant.upserts == []
    assert qdrant.deletes == []


def test_rerun_produces_the_same_point_ids(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, APPROVED_ROW)

    sync.sync_review_log(path)
    sync.sync_review_log(path)

    first, second = qdrant.upserts
    assert first.id == second.id


def test_prune_deletes_only_non_approved_ids(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, APPROVED_ROW + PENDING_ROW + DENIED_ROW)

    summary = sync.sync_review_log(path, prune=True)

    approved_id = sync.point_id_for("2026-10-20T13:04:52+00:00", "What is MFA?")
    assert summary["pruned"] == 2
    assert [point.id for point in qdrant.upserts] == [approved_id]
    assert approved_id not in qdrant.deletes
    assert set(qdrant.deletes) == {
        sync.point_id_for("2026-10-20T16:17:33+00:00", "How do I secure Kubernetes?"),
        sync.point_id_for("2026-10-20T16:20:37+00:00", "Who won the game?"),
    }


def test_unknown_status_aborts_before_any_write(tmp_path, qdrant) -> None:
    bad_row = '2026-10-21T09:00:00+00:00,Is MFA good?,"x",approve\n'
    path = write_log(tmp_path, APPROVED_ROW + bad_row)

    with pytest.raises(sync.SyncError, match="unknown status"):
        sync.sync_review_log(path)
    assert qdrant.upserts == []


def test_approved_row_without_answer_aborts_before_any_write(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, APPROVED_ROW + '2026-10-21T09:00:00+00:00,Is MFA good?,"",approved_review\n')

    with pytest.raises(sync.SyncError, match="approved but model_answer is empty"):
        sync.sync_review_log(path)
    assert qdrant.upserts == []


def test_answer_column_is_used_when_present(tmp_path, qdrant) -> None:
    header = "timestamp_utc,question,model_answer,answer,status\n"
    row = '2026-10-20T13:04:52+00:00,What is MFA?,"draft","reviewed text",approved_review\n'
    path = write_log(tmp_path, row, header=header)

    sync.sync_review_log(path)

    assert qdrant.upserts[0].payload["answer"] == "reviewed text"


def test_missing_required_column_aborts(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, "", header="timestamp_utc,model_answer\n")

    with pytest.raises(sync.SyncError, match="missing columns"):
        sync.sync_review_log(path)
    assert qdrant.upserts == []


def test_duplicate_rows_abort_before_any_write(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, APPROVED_ROW + APPROVED_ROW)

    with pytest.raises(sync.SyncError, match="duplicate"):
        sync.sync_review_log(path)
    assert qdrant.upserts == []


def test_dry_run_reports_stale_points_without_deleting(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, APPROVED_ROW)
    stale_id = sync.point_id_for("2026-10-19T08:00:00+00:00", "Old question?")
    qdrant.stored = {stale_id: "Question: Old question?\nAnswer: old"}

    summary = sync.sync_review_log(path, dry_run=True)

    assert summary["stale"] == 1
    assert qdrant.deletes == []


def test_prune_removes_stale_points(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, APPROVED_ROW)
    stale_id = sync.point_id_for("2026-10-19T08:00:00+00:00", "Old question?")
    qdrant.stored = {
        stale_id: "Question: Old question?\nAnswer: old",
        sync.point_id_for("2026-10-20T13:04:52+00:00", "What is MFA?"): "stale text",
    }

    summary = sync.sync_review_log(path, prune=True)

    assert summary["stale"] == 1
    assert summary["pruned"] == 1
    assert qdrant.deletes == [stale_id]


def test_unchanged_approved_row_is_not_upserted(tmp_path, qdrant) -> None:
    path = write_log(tmp_path, APPROVED_ROW)
    approved_id = sync.point_id_for("2026-10-20T13:04:52+00:00", "What is MFA?")
    qdrant.stored = {approved_id: "Question: What is MFA?\nAnswer: A second verification factor."}

    summary = sync.sync_review_log(path)

    assert summary["approved"] == 0
    assert summary["unchanged"] == 1
    assert summary["upserted"] == 0
    assert summary["status"] == "done_success"
    assert qdrant.upserts == []
