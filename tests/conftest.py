import pytest


@pytest.fixture(autouse=True)
def isolate_unanswered_fallback(monkeypatch, tmp_path):
    async def no_model_answer(question):
        return ""

    monkeypatch.setattr(
        "agents.tools.agents.retrieval.agent.generate_model_answer",
        no_model_answer,
    )
    monkeypatch.setenv("UNANSWERED_LOG_PATH", str(tmp_path / "unanswered.csv"))
