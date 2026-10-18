import httpx

from agents.preflight import (
    check_ollama,
    check_qdrant,
    missing_models,
    normalize_model_name,
)


def test_normalize_model_name_adds_latest_tag_only_when_missing():
    assert normalize_model_name("nomic-embed-text") == "nomic-embed-text:latest"
    assert normalize_model_name("qwen2.5:7b") == "qwen2.5:7b"


def test_missing_models_treats_untagged_names_as_latest():
    installed = ["qwen2.5:7b", "nomic-embed-text:latest"]
    assert missing_models(["qwen2.5:7b", "nomic-embed-text"], installed) == []
    assert missing_models(["llama3"], installed) == ["llama3"]


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_check_ollama_reports_missing_model():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "qwen2.5:7b"}]})

    check = check_ollama(_client(handler), "http://ollama", ["qwen2.5:7b", "nomic-embed-text"])
    assert not check.ok
    assert "nomic-embed-text" in check.detail


def test_check_ollama_passes_when_all_models_present():
    def handler(request):
        return httpx.Response(
            200,
            json={"models": [{"name": "qwen2.5:7b"}, {"name": "nomic-embed-text:latest"}]},
        )

    assert check_ollama(_client(handler), "http://ollama", ["qwen2.5:7b", "nomic-embed-text"]).ok


def test_check_qdrant_fails_on_missing_or_empty_collection():
    def missing(request):
        return httpx.Response(404, json={"status": {"error": "not found"}})

    def empty(request):
        return httpx.Response(200, json={"result": {"points_count": 0}})

    assert not check_qdrant(_client(missing), "http://qdrant", "multi_agentic_rag", None).ok
    assert not check_qdrant(_client(empty), "http://qdrant", "multi_agentic_rag", None).ok


def test_check_qdrant_passes_with_points():
    def handler(request):
        return httpx.Response(200, json={"result": {"points_count": 42}})

    check = check_qdrant(_client(handler), "http://qdrant", "multi_agentic_rag", None)
    assert check.ok
    assert "42" in check.detail
