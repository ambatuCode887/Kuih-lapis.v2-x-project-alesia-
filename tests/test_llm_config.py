from agents import config


def test_agent_model_uses_openrouter_when_configured(monkeypatch) -> None:
    captured = {}

    class FakeLiteLlm:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("google.adk.models.lite_llm.LiteLlm", FakeLiteLlm)
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    config.agent_model()

    assert captured == {
        "model": "openrouter/nvidia/nemotron-3.5-lightning:free"
    }