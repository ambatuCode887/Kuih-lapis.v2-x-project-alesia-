import asyncio
import csv
import io
from pathlib import Path
from types import SimpleNamespace

from google.adk.agents.base_agent import BaseAgent
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from PIL import Image
from pypdf import PdfWriter

from agents.agent import (
    _ROOT_INSTRUCTION,
    _append_specialist_report,
    _cached_followup_response,
    _followup_suggestions,
    root_agent,
    route_request_to_agent,
    should_route_to_retrieval,
)
from agents.tools.agents.coordinator_agents.agent import (
    parse_assessment,
    select_follow_up_agent,
)
from agents.tools.agents.retrieval.agent import retrieval_agent


def test_cybersecurity_knowledge_questions_route_to_retrieval() -> None:
    assert should_route_to_retrieval(
        "How do I identify and remove malware from my computer?"
    )
    assert should_route_to_retrieval("What is credential stuffing?")


def test_artifact_analysis_requests_bypass_knowledge_route() -> None:
    assert not should_route_to_retrieval("Is this email a phishing attempt?")
    assert not should_route_to_retrieval("Check this link: https://example.com/login")
    assert route_request_to_agent("Example link, is this a malicious link?") == "url_check_agent"


def test_root_generates_retrieval_followups_without_qdrant_question_records() -> None:
    assert "model-generated follow-up questions" in _ROOT_INSTRUCTION
    assert "do not copy questions from retrieved Qdrant records" in _ROOT_INSTRUCTION
    assert "When no relevant evidence was returned, ask useful questions" in _ROOT_INSTRUCTION


def test_root_includes_malaysia_scam_reporting_resources() -> None:
    assert "Malaysian NSRC hotline (dial 997)" in _ROOT_INSTRUCTION
    assert "https://nfcc.jpm.gov.my/index.php/en/" in _ROOT_INSTRUCTION


def test_root_includes_mule_account_lookup_guidance() -> None:
    assert "When the user asks about or mentions mule accounts" in _ROOT_INSTRUCTION
    assert "https://semakmule.rmp.gov.my/" in _ROOT_INSTRUCTION


def test_root_routes_directly_to_specialist_agents() -> None:
    assert route_request_to_agent("Is this email a phishing attempt?") == "message_agent"
    assert route_request_to_agent("Check this link: https://example.com/login") == "url_check_agent"
    assert route_request_to_agent("Classify this precomputed feature vector") == "file_classifier_agent"
    assert route_request_to_agent("How do I remove malware?") == "retrieval_agent"
    assert (
        route_request_to_agent(
            "Is this attachment suspicious?",
            attachment_present=True,
        )
        == "message_agent"
    )


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


def test_routing_eval_dataset() -> None:
    dataset_path = (
        Path(__file__).resolve().parents[1]
        / "agents"
        / "eval"
        / "routing_cases.csv"
    )
    with dataset_path.open(newline="", encoding="utf-8") as handle:
        cases = list(csv.DictReader(handle))

    mismatches = []
    for case in cases:
        actual_route = route_request_to_agent(
            case["request"],
            attachment_present=case["has_attachment"].casefold() == "true",
        )
        if actual_route != case["expected_route"]:
            mismatches.append(
                f'{case["id"]}: expected {case["expected_route"]}, '
                f"got {actual_route} for {case['request']!r}"
            )

    assert len(cases) >= 40, "Routing evaluation set needs broader coverage."
    assert not mismatches, "\n".join(mismatches)


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
    assert request.config.tools is None
    assert request.tools_dict == {}
    assert request.config.tool_config.function_calling_config.mode == "NONE"


def test_root_removes_binary_upload_parts_before_text_model() -> None:
    request = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(text="Please analyze this screenshot."),
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="image/png",
                            data=b"image bytes",
                        )
                    ),
                ],
            )
        ]
    )
    callback_context = SimpleNamespace(
        state={"root_specialist_report": "Extracted screenshot text."}
    )

    _append_specialist_report(callback_context, request)

    assert all(part.text is not None for part in request.contents[0].parts)
    assert "Extracted screenshot text." in request.contents[0].parts[-1].text


def test_retrieval_specialist_returns_evidence_without_an_llm(monkeypatch) -> None:
    monkeypatch.setattr(
        "agents.tools.agents.retrieval.agent.retrieve_knowledge",
        lambda query: {
            "query": query,
            "results": [
                {
                    "score": 0.91,
                    "text": (
                        "Question: How do I protect login accounts?\n"
                        "Answer: Use a password manager and enable MFA."
                    ),
                    "source": "security.csv",
                    "chunk_index": 12,
                    "metadata": {"category": "Authentication"},
                }
            ],
        },
    )
    agent = retrieval_agent()
    context = SimpleNamespace(
        user_content=types.Content(
            role="user",
            parts=[types.Part(text="How can I secure my accounts?")],
        ),
        invocation_id="retrieval-test",
    )

    async def collect_events():
        return [event async for event in agent._run_async_impl(context)]

    events = asyncio.run(collect_events())

    assert isinstance(agent, BaseAgent)
    assert not hasattr(agent, "model")
    assert len(events) == 1
    assert events[0].is_final_response()
    assert "source=security.csv" in events[0].content.parts[0].text
    assert "chunk_index=12" in events[0].content.parts[0].text
    assert "Use a password manager" in events[0].content.parts[0].text
    assert events[0].actions.state_delta["cached_followups"] == [
        {
            "question": "How do I protect login accounts?",
            "answer": "Use a password manager and enable MFA.",
            "source": "security.csv",
            "chunk_index": "12",
        }
    ]


def test_followup_answers_are_served_from_cache_with_citation() -> None:
    followups = [
        {
            "question": "What is MFA?",
            "answer": "MFA uses more than one verification factor.",
            "source": "security.csv",
            "chunk_index": "12",
        }
    ]

    response = _cached_followup_response("What is MFA?!", followups)

    assert response == (
        "MFA uses more than one verification factor.\n\n"
        "Source: security.csv, chunk 12."
    )


def test_followup_suggestions_use_only_cached_questions() -> None:
    suggestions = _followup_suggestions(
        [{"question": "What is MFA?", "answer": "A second factor."}]
    )

    assert "What is MFA?" in suggestions
    assert "instant cached answer" in suggestions


def test_root_answers_cached_followup_without_running_specialists() -> None:
    context = SimpleNamespace(
        user_content=types.Content(
            role="user",
            parts=[types.Part(text="What is MFA?")],
        ),
        invocation_id="cached-followup-test",
        session=SimpleNamespace(
            state={
                "cached_followups": [
                    {
                        "question": "What is MFA?",
                        "answer": "MFA uses more than one verification factor.",
                        "source": "security.csv",
                        "chunk_index": "12",
                    }
                ]
            }
        ),
    )

    async def collect_events():
        return [event async for event in root_agent._run_async_impl(context)]

    events = asyncio.run(collect_events())

    assert len(events) == 1
    assert events[0].author == "root_agent"
    assert events[0].is_final_response()
    assert "MFA uses more than one verification factor." in events[0].content.parts[0].text
    assert "Source: security.csv, chunk 12." in events[0].content.parts[0].text


def test_message_agent_detects_adk_inline_uploads() -> None:
    from agents.tools.agents.message_agents.attachments import has_attachment

    content = types.Content(
        role="user",
        parts=[
            types.Part(
                inline_data=types.Blob(
                    mime_type="image/png",
                    data=b"image bytes",
                    display_name="screenshot.png",
                )
            )
        ],
    )

    assert has_attachment(content)


def test_router_redacts_binary_attachments_from_prior_turns() -> None:
    from agents.tools.agents.message_agents.attachments import (
        redact_historical_attachments,
    )

    prior_upload = SimpleNamespace(
        author="user",
        invocation_id="upload-turn",
        content=types.Content(
            role="user",
            parts=[
                types.Part(text="Please inspect this screenshot."),
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=b"image bytes",
                    )
                ),
            ],
        ),
    )
    followup = SimpleNamespace(
        author="user",
        invocation_id="followup-turn",
        content=types.Content(role="user", parts=[types.Part(text="What next?")]),
    )
    session = SimpleNamespace(events=[prior_upload, followup])

    redact_historical_attachments(session, "followup-turn")

    prior_parts = prior_upload.content.parts
    assert any(part.text == "Please inspect this screenshot." for part in prior_parts)
    assert any("Prior attachment omitted" in part.text for part in prior_parts)
    assert all(part.inline_data is None and part.file_data is None for part in prior_parts)
    assert followup.content.parts[0].text == "What next?"


def test_message_agent_preprocesses_artifact_reference(monkeypatch) -> None:
    from agents.tools.agents.message_agents.attachments import prepare_message_attachments

    artifact = types.Part(
        inline_data=types.Blob(
            mime_type="image/png",
            data=b"image bytes",
        )
    )
    monkeypatch.setattr(
        "agents.tools.agents.message_agents.attachments._load_artifact",
        lambda context, filename: asyncio.sleep(0, result=artifact),
    )
    monkeypatch.setattr(
        "agents.tools.agents.message_agents.attachments._extract_attachment",
        lambda name, mime_type, data: "Extracted artifact text",
    )
    user_event = SimpleNamespace(
        author="user",
        invocation_id="artifact-test",
        content=types.Content(
            role="user",
            parts=[types.Part(text='Please inspect [Uploaded Artifact: "capture.png"]')],
        ),
    )
    context = SimpleNamespace(
        artifact_service=object(),
        app_name="agents",
        user_id="artifact-test",
        invocation_id="artifact-test",
        session=SimpleNamespace(id="artifact-test", events=[user_event]),
        user_content=user_event.content,
    )
    callback_context = SimpleNamespace(
        get_invocation_context=lambda: context,
    )
    request = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(text='Please inspect [Uploaded Artifact: "capture.png"]')
                ],
            )
        ]
    )

    asyncio.run(prepare_message_attachments(callback_context, request))

    report = "\n".join(part.text for part in request.contents[0].parts)
    assert "Please inspect" in report
    assert "File: capture.png" in report
    assert "Extracted artifact text" in report
    assert all(part.inline_data is None and part.file_data is None for part in request.contents[0].parts)
    assert all(part.inline_data is None and part.file_data is None for part in user_event.content.parts)


def test_scanned_pdf_pages_are_ocr_processed(monkeypatch) -> None:
    from agents.tools.agents.message_agents.attachments import _extract_attachment

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    pdf_bytes = io.BytesIO()
    writer.write(pdf_bytes)
    monkeypatch.setattr(
        "agents.tools.agents.message_agents.attachments._ocr_image",
        lambda image: "OCR text from scanned page",
    )

    result = _extract_attachment("scan.pdf", "application/pdf", pdf_bytes.getvalue())

    assert "[Page 1]" in result
    assert "OCR text from scanned page" in result


def test_image_attachment_uses_local_ocr(monkeypatch) -> None:
    from agents.tools.agents.message_agents.attachments import _extract_attachment

    image_bytes = io.BytesIO()
    Image.new("RGB", (2, 2), color="white").save(image_bytes, format="PNG")
    monkeypatch.setattr(
        "agents.tools.agents.message_agents.attachments._ocr_image",
        lambda image: "Visible screenshot text",
    )

    result = _extract_attachment("screen.png", "image/png", image_bytes.getvalue())

    assert result == "Visible screenshot text"