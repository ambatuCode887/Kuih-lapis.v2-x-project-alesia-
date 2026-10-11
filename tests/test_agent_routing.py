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
from agents.tools.agents.coordinator_agents.agent import (
    parse_assessment,
    select_follow_up_agent,
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
        "coordinator_agent",
    }


def test_coordinator_routes_low_confidence_to_clarification() -> None:
    assert select_follow_up_agent({"confidence": 50}) == "clarification_agent"
    assert select_follow_up_agent({"confidence": 59}) == "clarification_agent"
    assert select_follow_up_agent(
        {"confidence": 50, "risk_level": "insufficient_information"}
    ) == "clarification_agent"


def test_coordinator_routes_sufficient_confidence_to_verification() -> None:
    assert select_follow_up_agent({"confidence": 60}) == "verification_agent"
    assert select_follow_up_agent({"confidence": 85}) == "verification_agent"


def test_coordinator_fails_safe_to_clarification_for_missing_or_invalid_confidence() -> None:
    assert select_follow_up_agent(None) == "clarification_agent"
    assert select_follow_up_agent({}) == "clarification_agent"
    assert select_follow_up_agent({"confidence": "50"}) == "clarification_agent"


def test_assessment_parser_reads_json_fenced_by_specialist() -> None:
    assessment = parse_assessment(
        '```json\n{"risk_score": null, "risk_level": "insufficient_information", '
        '"confidence": 50}\n```'
    )
    assert assessment == {
        "risk_score": None,
        "risk_level": "insufficient_information",
        "confidence": 50,
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