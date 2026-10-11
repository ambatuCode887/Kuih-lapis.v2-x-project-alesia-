from types import SimpleNamespace

from google.adk.models.llm_request import LlmRequest
from google.genai import types

from agents.agent import (
    _ROOT_INSTRUCTION,
    _append_specialist_report,
    root_agent,
    route_request_to_agent,
    should_route_to_retrieval,
)


def test_cybersecurity_knowledge_questions_route_to_retrieval() -> None:
    assert should_route_to_retrieval(
        "How do I identify and remove malware from my computer?"
    )
    assert should_route_to_retrieval("What is credential stuffing?")


def test_artifact_analysis_requests_bypass_knowledge_route() -> None:
    assert not should_route_to_retrieval("Is this email a phishing attempt?")
    assert not should_route_to_retrieval("Check this link: https://example.com/login")


def test_root_routes_directly_to_specialist_agents() -> None:
    assert route_request_to_agent("Is this email a phishing attempt?") == "message_agent"
    assert route_request_to_agent("Check this link: https://example.com/login") == "url_check_agent"
    assert route_request_to_agent("Classify this precomputed feature vector") == "file_classifier_agent"
    assert route_request_to_agent("How do I remove malware?") == "retrieval_agent"


def test_root_router_has_final_response_model_and_dispatches_to_specialists() -> None:
    assert root_agent.model is not None
    assert root_agent.instruction == _ROOT_INSTRUCTION
    assert {agent.name for agent in root_agent.sub_agents} == {
        "message_agent",
        "url_check_agent",
        "file_classifier_agent",
        "retrieval_agent",
    }


def test_specialist_report_is_appended_as_user_data_not_system_instruction() -> None:
    request = LlmRequest(
        contents=[types.Content(role="user", parts=[types.Part(text="Question?")])]
    )
    callback_context = SimpleNamespace(
        state={"root_specialist_report": "Evidence (source.csv, row 3)."}
    )

    _append_specialist_report(callback_context, request)

    assert request.contents[0].parts[0].text == "Question?"
    assert "Evidence (source.csv, row 3)." in request.contents[0].parts[1].text
    assert "untrusted evidence" in request.contents[0].parts[1].text