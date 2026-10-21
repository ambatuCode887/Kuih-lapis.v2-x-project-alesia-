from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.tools.functions.embeddings import embed_texts
from agents.tools.functions.qdrant_store import client, ensure_collection, settings
from agents.tools.functions.unanswered_log import unanswered_log_path

SOURCE = "unanswered_questions"
APPROVED = "approved_review"
STATUSES = {APPROVED, "denied_review", "pending_review"}
REQUIRED_COLUMNS = {"timestamp_utc", "question", "status"}
BATCH_SIZE = 64


class SyncError(ValueError):
    """The review log failed validation; no points were written."""


@dataclass(frozen=True)
class ReviewRow:
    point_id: str
    timestamp_utc: str
    question: str
    answer: str
    status: str


def point_id_for(timestamp_utc: str, question: str) -> str:
    raw = f"{SOURCE}:{timestamp_utc}:{question}".encode("utf-8")
    return str(uuid.UUID(hashlib.sha256(raw).hexdigest()[:32]))


def _text(row: ReviewRow) -> str:
    return f"Question: {row.question}\nAnswer: {row.answer}"


def read_review_log(path: Path) -> tuple[list[ReviewRow], list[ReviewRow]]:
    """Validate the whole log and return (approved rows, rows that are not approved)."""
    if not path.exists():
        raise SyncError(f"review log not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise SyncError(f"missing columns: {sorted(missing)}")
        answer_column = "answer" if "answer" in columns else "model_answer"
        if answer_column not in columns:
            raise SyncError("needs an 'answer' or 'model_answer' column")
        records = list(reader)

    approved: list[ReviewRow] = []
    not_approved: list[ReviewRow] = []
    seen: set[str] = set()
    for number, record in enumerate(records, start=1):
        status = (record.get("status") or "").strip()
        timestamp = (record.get("timestamp_utc") or "").strip()
        question = (record.get("question") or "").strip()
        answer = (record.get(answer_column) or "").strip()
        if status not in STATUSES:
            raise SyncError(f"row {number}: unknown status {status!r}")
        if not timestamp or not question:
            raise SyncError(f"row {number}: timestamp_utc and question are required")
        point_id = point_id_for(timestamp, question)
        if point_id in seen:
            raise SyncError(f"row {number}: duplicate of an earlier timestamp and question")
        seen.add(point_id)

        row = ReviewRow(point_id, timestamp, question, answer, status)
        if status != APPROVED:
            not_approved.append(row)
        elif not answer:
            raise SyncError(f"row {number}: approved but {answer_column} is empty")
        else:
            approved.append(row)
    return approved, not_approved


def _point(row: ReviewRow, vector: list[float]) -> Any:
    from qdrant_client.models import PointStruct

    return PointStruct(
        id=row.point_id,
        vector=vector,
        payload={
            "text": _text(row),
            "source": SOURCE,
            "chunk_index": 0,
            "question": row.question,
            "answer": row.answer,
            "review_status": row.status,
            "timestamp_utc": row.timestamp_utc,
        },
    )


def stored_point_ids(qdrant: Any, collection: str) -> set[str]:
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    flt = Filter(must=[FieldCondition(key="source", match=MatchValue(value=SOURCE))])
    ids: set[str] = set()
    offset = None
    while True:
        points, offset = qdrant.scroll(
            collection_name=collection,
            scroll_filter=flt,
            limit=256,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        ids.update(str(point.id) for point in points)
        if offset is None:
            return ids


def sync_review_log(path: Path, *, dry_run: bool = False, prune: bool = False) -> dict[str, Any]:
    """Upsert approved rows; pruning is opt-in and deletes non-approved and stale point IDs."""
    approved, not_approved = read_review_log(path)
    cfg = settings()
    qdrant = client()
    current_ids = {row.point_id for row in approved + not_approved}
    stale_ids = sorted(stored_point_ids(qdrant, cfg.collection) - current_ids)
    summary: dict[str, Any] = {
        "file": str(path),
        "approved": len(approved),
        "not_approved": len(not_approved),
        "stale": len(stale_ids),
        "dry_run": dry_run,
        "upserted": 0,
        "pruned": 0,
    }
    if dry_run:
        summary["would_prune"] = len(not_approved) + len(stale_ids) if prune else 0
        return summary

    ensure_collection()
    if approved:
        vectors = embed_texts([_text(row) for row in approved])
        points = [_point(row, vector) for row, vector in zip(approved, vectors, strict=True)]
        for start in range(0, len(points), BATCH_SIZE):
            qdrant.upsert(
                collection_name=cfg.collection,
                points=points[start : start + BATCH_SIZE],
                wait=True,
            )
        summary["upserted"] = len(points)

    if prune and (not_approved or stale_ids):
        from qdrant_client.models import PointIdsList

        delete_ids = [row.point_id for row in not_approved] + stale_ids
        qdrant.delete(
            collection_name=cfg.collection,
            points_selector=PointIdsList(points=delete_ids),
            wait=True,
        )
        summary["pruned"] = len(delete_ids)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upsert approved_review rows from the unanswered log into Qdrant."
    )
    parser.add_argument("--csv", type=Path, help="review log path (default: UNANSWERED_LOG_PATH)")
    parser.add_argument("--dry-run", action="store_true", help="validate and report without writing")
    parser.add_argument(
        "--prune",
        action="store_true",
        help="also delete points for rows that are not approved_review",
    )
    args = parser.parse_args(argv)
    try:
        summary = sync_review_log(
            args.csv or unanswered_log_path(),
            dry_run=args.dry_run,
            prune=args.prune,
        )
    except SyncError as error:
        print(f"Sync aborted, nothing written: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
