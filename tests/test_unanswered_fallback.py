import asyncio
import csv
from types import SimpleNamespace

from google.genai import types

from agents.tools.agents.retrieval import agent as retrieval
from agents.tools.functions.unanswered_log import append_unanswered


def _run_miss(question: str):
    agent = retrieval.retrieval_agent()
    context = SimpleNamespace(
        user_content=types.Content(role="user", parts=[types.Part(text=question)]),
        invocation_id="unanswered-test",
    )

    async def collect_events():
        return [event async for event in agent._run_async_impl(context)]

    return asyncio.run(collect_events())


def _rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_knowledge_miss_returns_labelled_model_answer_and_logs_row(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "unanswered.csv"
    monkeypatch.setenv("UNANSWERED_LOG_PATH", str(log_path))

    async def fake_answer(question):
        return "Multi-factor authentication adds a second check to a login."

    monkeypatch.setattr("agents.tools.agents.retrieval.agent.generate_model_answer", fake_answer)
    monkeypatch.setattr(
        "agents.tools.agents.retrieval.agent.retrieve_knowledge",
        lambda query: {"results": []},
    )

    events = _run_miss("What is MFA?")
    text = events[0].content.parts[0].text

    assert "I couldn't find a matching answer in the available knowledge sources." not in text
    assert "Model answer (not from the knowledge base, unverified):" not in text
    assert "second check to a login" in text
    rows = _rows(log_path)
    assert len(rows) == 1
    assert rows[0]["question"] == "What is MFA?"
    assert rows[0]["model_answer"] == "Multi-factor authentication adds a second check to a login."
    assert rows[0]["status"] == "pending_review"


def test_model_failure_still_logs_question_without_answer(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "unanswered.csv"
    monkeypatch.setenv("UNANSWERED_LOG_PATH", str(log_path))

    async def offline(question):
        raise ConnectionError("Ollama is not running")

    monkeypatch.setattr("agents.tools.agents.retrieval.agent.generate_model_answer", offline)
    monkeypatch.setattr(
        "agents.tools.agents.retrieval.agent.retrieve_knowledge",
        lambda query: {"results": []},
    )

    events = _run_miss("What is a honeypot?")
    text = events[0].content.parts[0].text

    assert text == "I don't have enough information to answer that reliably right now."
    rows = _rows(log_path)
    assert rows[0]["question"] == "What is a honeypot?"
    assert rows[0]["model_answer"] == ""
    assert rows[0]["status"] == "no_model_answer"


def test_knowledge_base_outage_is_not_logged_as_unanswered(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "unanswered.csv"
    monkeypatch.setenv("UNANSWERED_LOG_PATH", str(log_path))

    def unavailable(query):
        raise RuntimeError("Qdrant is down")

    monkeypatch.setattr("agents.tools.agents.retrieval.agent.retrieve_knowledge", unavailable)

    _run_miss("What is MFA?")

    assert not log_path.exists()


def test_formula_like_cells_are_stored_as_text(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "unanswered.csv"
    monkeypatch.setenv("UNANSWERED_LOG_PATH", str(log_path))

    append_unanswered('=HYPERLINK("http://evil.example","click")', "+1 555", "no_model_answer")

    rows = _rows(log_path)
    assert rows[0]["question"] == "'=HYPERLINK(\"http://evil.example\",\"click\")"
    assert rows[0]["model_answer"] == "'+1 555"


def test_private_and_sensitive_content_is_redacted_before_storage(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "unanswered.csv"
    monkeypatch.setenv("UNANSWERED_LOG_PATH", str(log_path))

    append_unanswered(
        "My IC is 900101-14-5678 and email me at user@example.com. "
        "Use https://example.com/reset?token=secret.",
        "That message contains shit and a phone number +60 12-345 6789.",
        "pending_review",
    )

    [row] = _rows(log_path)
    assert "900101-14-5678" not in row["question"]
    assert "user@example.com" not in row["question"]
    assert "token=secret" not in row["question"]
    assert "+60 12-345 6789" not in row["model_answer"]
    assert "[REDACTED_ID]" in row["question"]
    assert "[REDACTED_EMAIL]" in row["question"]
    assert "[REDACTED_QUERY]" in row["question"]
    assert "[REDACTED_PHONE]" in row["model_answer"]
    assert "shit" not in row["model_answer"].casefold()
    assert "[REDACTED_SENSITIVE_LANGUAGE]" in row["model_answer"]


def test_log_appends_without_rewriting_earlier_rows(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "unanswered.csv"
    monkeypatch.setenv("UNANSWERED_LOG_PATH", str(log_path))

    append_unanswered("First question?", "First answer.", "pending_review")
    append_unanswered("Second question?", "", "no_model_answer")

    rows = _rows(log_path)
    assert [row["question"] for row in rows] == ["First question?", "Second question?"]
    assert rows[0]["status"] == "pending_review"
