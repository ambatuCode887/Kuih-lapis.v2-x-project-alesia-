import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "browser: drives the built Chrome extension with Playwright")
    config.addinivalue_line("markers", "backend: needs the backend running on port 8000")


@pytest.fixture(autouse=True)
def isolate_unanswered_fallback(monkeypatch, tmp_path):
    async def no_model_answer(question):
        return ""

    monkeypatch.setattr(
        "agents.tools.agents.retrieval.agent.generate_model_answer",
        no_model_answer,
    )
    monkeypatch.setenv("UNANSWERED_LOG_PATH", str(tmp_path / "unanswered.csv"))
    monkeypatch.setenv("REVIEW_SHEET_ID", "")
