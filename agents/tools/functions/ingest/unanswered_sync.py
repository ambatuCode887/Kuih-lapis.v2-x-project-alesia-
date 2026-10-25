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

from agents.tools.functions import review_sheet
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
    """Validate the CSV review log and return (approved rows, rows that are not approved)."""
    if not path.exists():
        raise SyncError(f"review log not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return _validate(list(reader.fieldnames or []), list(reader))


def read_review_sheet() -> tuple[list[ReviewRow], list[ReviewRow]]:
    """Validate the shared review sheet with the same rules as the CSV log."""
    try:
        columns, records = review_sheet.read_rows()
    except review_sheet.ReviewSheetError as error:
        raise SyncError(f"could not read review sheet: {error}") from error
    return _validate(columns, records)


def _validate(columns: list[str], records: list[dict[str, str]]) -> tuple[list[ReviewRow], list[ReviewRow]]:
    column_set = set(columns)
    missing = REQUIRED_COLUMNS - column_set
    if missing:
        raise SyncError(f"missing columns: {sorted(missing)}")
    answer_column = "answer" if "answer" in column_set else "model_answer"
    if answer_column not in column_set:
        raise SyncError("needs an 'answer' or 'model_answer' column")

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


def stored_texts(qdrant: Any, collection: str) -> dict[str, str]:
    stored: dict[str, str] = {}
    offset = None
    while True:
        points, offset = qdrant.scroll(
            collection_name=collection,
            limit=256,
            offset=offset,
            with_payload=["source", "text"],
            with_vectors=False,
        )
        for point in points:
            payload = point.payload or {}
            if payload.get("source") == SOURCE:
                stored[str(point.id)] = payload.get("text", "")
        if offset is None:
            return stored


def sync_review_log(path: Path | None, *, dry_run: bool = False, prune: bool = False) -> dict[str, Any]:
    """Upsert approved rows from a CSV (or the review sheet when path is None); pruning is opt-in."""
    approved, not_approved = read_review_sheet() if path is None else read_review_log(path)
    cfg = settings()
    qdrant = client()
    stored = stored_texts(qdrant, cfg.collection)
    current_ids = {row.point_id for row in approved + not_approved}
    stale_ids = sorted(set(stored) - current_ids)
    changed = [row for row in approved if stored.get(row.point_id) != _text(row)]
    summary: dict[str, Any] = {
        "file": str(path) if path is not None else "review_sheet",
        "approved": len(changed),
        "unchanged": len(approved) - len(changed),
        "not_approved": len(not_approved),
        "stale": len(stale_ids),
        "dry_run": dry_run,
        "upserted": 0,
        "pruned": 0,
        "status": "dry_run_success" if dry_run else "done_success",
    }
    if dry_run:
        summary["would_prune"] = len(not_approved) + len(stale_ids) if prune else 0
        return summary

    ensure_collection()
    if changed:
        vectors = embed_texts([_text(row) for row in changed])
        points = [_point(row, vector) for row, vector in zip(changed, vectors, strict=True)]
        for start in range(0, len(points), BATCH_SIZE):
            qdrant.upsert(
                collection_name=cfg.collection,
                points=points[start : start + BATCH_SIZE],
                wait=True,
            )
        summary["upserted"] = len(points)

    if prune and (not_approved or stale_ids):
        from qdrant_client.models import ExtendedPointId, PointIdsList

        delete_ids: list[ExtendedPointId] = [row.point_id for row in not_approved]
        delete_ids.extend(stale_ids)
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
    parser.add_argument("--csv", type=Path, help="read this CSV instead of the review sheet")
    parser.add_argument("--dry-run", action="store_true", help="validate and report without writing")
    parser.add_argument(
        "--prune",
        action="store_true",
        help="also delete points for rows that are not approved_review",
    )
    args = parser.parse_args(argv)
    source = args.csv or (None if review_sheet.is_configured() else unanswered_log_path())
    try:
        summary = sync_review_log(
            source,
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
