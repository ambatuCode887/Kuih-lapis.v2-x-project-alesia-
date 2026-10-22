import json

from agents.tools.functions.incident import build_incident_plan
from agents.tools.functions.incident.audit import AuditLog, case_record


def _log(n=3):
    log = AuditLog(clock=lambda: 1.0)
    for i in range(n):
        log.append("step", {"i": i})
    return log


def test_chain_verifies():
    assert _log().verify().ok


def test_edit_is_detected():
    log = _log()
    log._entries[1]["payload"]["i"] = 99
    result = log.verify()
    assert not result.ok and result.broken_at == 1


def test_delete_and_reorder_are_detected():
    log = _log(4)
    del log._entries[1]
    assert not log.verify().ok
    log2 = _log(3)
    log2._entries[0], log2._entries[1] = log2._entries[1], log2._entries[0]
    assert not log2.verify().ok


def test_truncation_detected_only_with_saved_head():
    log = _log(3)
    head = log.head_hash
    del log._entries[-1]
    assert log.verify().ok  # documented limit
    assert not log.verify(expected_head=head).ok


def test_payload_is_redacted():
    log = AuditLog()
    log.append("note", {"text": "mail a@example.com token=abc123 IC 900101-14-5678"})
    dumped = json.dumps(log.entries)
    for leaked in ("a@example.com", "abc123", "900101"):
        assert leaked not in dumped


def test_file_backed_log_reloads_and_verifies(tmp_path):
    path = tmp_path / "audit.jsonl"
    a = AuditLog(path)
    a.append("x", {"k": 1})
    a.append("y", {})
    b = AuditLog(path)
    assert b.verify().ok and len(b.entries) == 2
    assert b.append("z", {})["prev_hash"] == a.head_hash


def test_case_record_has_no_raw_text_and_does_not_self_complete_steps():
    text = "A scammer made me transfer RM3000 to 0123456789; I transferred it and my IC is 900101-14-5678"
    plan = build_incident_plan(text)
    rec = case_record(plan, "case-1")
    blob = json.dumps(rec)
    assert "900101" not in blob and "0123456789" not in blob
    assert not any(s["done_by_user"] for s in rec["steps"])
    assert "money_sent" in rec["facts_reported_by_user"]
    done = case_record(plan, "case-1", {rec["steps"][0]["id"]: True})
    assert done["steps"][0]["done_by_user"]
