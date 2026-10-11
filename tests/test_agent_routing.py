from agents.agent import root_agent, route_request_to_agent, should_route_to_retrieval


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


def test_root_router_has_no_language_model_and_dispatches_to_children() -> None:
    assert not hasattr(root_agent, "model")
    assert {agent.name for agent in root_agent.sub_agents} == {
        "message_agent",
        "url_check_agent",
        "file_classifier_agent",
        "retrieval_agent",
    }