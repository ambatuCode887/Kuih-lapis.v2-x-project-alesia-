"""Tamper-evident, hash-chained audit trail and case records for incidents.

Each entry stores the SHA-256 of its canonical JSON including the previous
entry's hash, so editing, deleting or reordering any entry breaks verification.

Limits (be honest about these in the demo):
* Tamper-EVIDENT, not tamper-PROOF: someone who can rewrite the whole file can
  recompute every hash. Publish or store ``head_hash`` somewhere separate to
  detect that, and truncating the tail is only caught if a head hash was kept.
* Payloads are passed through ``redact`` first, but redaction is best-effort.
* Nothing here contacts anyone or performs a containment action; it records only.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .playbook import IncidentPlan
from .redaction import redact

GENESIS = "0" * 64


def _canonical(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value).text
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value(v) for v in value]
    return value


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    entries: int
    broken_at: int | None = None
    reason: str = ""


class AuditLog:
    """Append-only log, in memory or backed by a JSONL file."""

    def __init__(self, path: str | Path | None = None, clock=time.time) -> None:
        self._path = Path(path) if path else None
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: list[dict[str, Any]] = []
        if self._path and self._path.exists():
            with self._path.open(encoding="utf-8") as fh:
                self._entries = [json.loads(line) for line in fh if line.strip()]

    @property
    def entries(self) -> list[dict[str, Any]]:
        return [dict(e) for e in self._entries]

    @property
    def head_hash(self) -> str:
        return self._entries[-1]["hash"] if self._entries else GENESIS

    def append(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            body = {
                "seq": len(self._entries),
                "ts": round(self._clock(), 3),
                "event": event_type,
                "payload": _redact_value(payload or {}),
                "prev_hash": self.head_hash,
            }
            entry = body | {"hash": hashlib.sha256(_canonical(body)).hexdigest()}
            self._entries.append(entry)
            if self._path:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
            return dict(entry)

    def verify(self, expected_head: str | None = None) -> VerifyResult:
        prev = GENESIS
        for i, entry in enumerate(self._entries):
            body = {k: v for k, v in entry.items() if k != "hash"}
            if entry.get("seq") != i:
                return VerifyResult(False, len(self._entries), i, "sequence gap or reorder")
            if entry.get("prev_hash") != prev:
                return VerifyResult(False, len(self._entries), i, "prev_hash mismatch")
            if hashlib.sha256(_canonical(body)).hexdigest() != entry.get("hash"):
                return VerifyResult(False, len(self._entries), i, "entry content altered")
            prev = entry["hash"]
        if expected_head is not None and expected_head != prev:
            return VerifyResult(False, len(self._entries), None, "head hash differs (truncation?)")
        return VerifyResult(True, len(self._entries))


def case_record(plan: IncidentPlan, case_id: str, user_confirmed: dict[str, bool] | None = None) -> dict[str, Any]:
    """Summarise a plan as a case record. Never stores the user's raw text.

    ``user_confirmed`` maps step id -> done, supplied by the user; nothing here
    marks a step done on its own. Facts (detected signals) and inferences
    (assessment influence) are kept in separate fields.
    """
    done = user_confirmed or {}
    return {
        "case_id": case_id,
        "severity": plan.severity,
        "language": plan.language,
        "facts_reported_by_user": sorted({s.kind for s in plan.signals if s.status == "confirmed"}),
        "possible_unconfirmed": sorted({s.kind for s in plan.signals if s.status != "confirmed"}),
        "inferences": {"assessment_influenced": plan.assessment_used},
        "steps": [{"id": s.id, "tier": s.tier, "done_by_user": bool(done.get(s.id))} for s in plan.steps],
        "open_questions": len(plan.questions),
        "untrusted_contact_seen": plan.untrusted_contact_seen,
    }
