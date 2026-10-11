from __future__ import annotations

import httpx

from agents.tools.functions.ingest import documents
from agents.tools.functions.publish.prepare import prepare_confluence_page
from agents.tools.functions.publish.result import publish_confluence_page


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


def test_publish_converters_support_common_markdown() -> None:
    prepared = prepare_confluence_page(
        "Title",
        "# Heading\n\nText **bold** and [link](https://example.com).\n\n- Item",
        space_key="TEST",
    )
    assert prepared["ok"]
    assert "<strong>bold</strong>" in prepared["payload"]["body"]
    assert "<a href=\"https://example.com\">link</a>" in prepared["payload"]["body"]


def test_invalid_body_format_is_rejected() -> None:
    result = prepare_confluence_page("Title", "Body", space_key="TEST", body_format="invalid")
    assert not result["ok"]
    assert "body_format" in result["errors"][0]


def test_empty_adf_is_rejected() -> None:
    result = prepare_confluence_page(
        "Title", "", space_key="TEST", body_format="atlas_doc_format"
    )
    assert not result["ok"]


def test_publish_returns_network_error(monkeypatch) -> None:
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://example.com")
    monkeypatch.setenv("CONFLUENCE_EMAIL", "user@example.com")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "token")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "TEST")

    def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("agents.tools.functions.publish.result.httpx.post", fail)
    result = publish_confluence_page("Title", "Body", dry_run=False)
    assert not result["ok"]
    assert "request failed" in result["errors"][0]
