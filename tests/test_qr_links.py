from __future__ import annotations

import asyncio
import io
from types import SimpleNamespace

import numpy as np
import pytest
import zxingcpp
from google.genai import types
from PIL import Image

from agents.tools.agents.coordinator_agents.agent import merge_assessments
from agents.tools.agents.message_agents import attachments
from agents.tools.agents.message_agents.qr import (
    decode_qr_payloads,
    qr_link_hosts,
    web_link_host,
)
from agents.tools.agents.url_check.domain_check import (
    download_assessment,
    qr_link_assessment,
)


def _qr_png(text: str) -> bytes:
    barcode = zxingcpp.create_barcode(text, zxingcpp.BarcodeFormat.QRCode)
    code = zxingcpp.write_barcode_to_image(barcode, scale=8)
    image = Image.fromarray(np.asarray(code)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_decodes_qr_payload_from_image() -> None:
    image = Image.open(io.BytesIO(_qr_png("https://login.example.test/reset")))

    assert decode_qr_payloads(image) == ["https://login.example.test/reset"]


def test_image_without_qr_has_no_payloads() -> None:
    assert decode_qr_payloads(Image.new("RGB", (200, 200), "white")) == []


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("https://Login.Example.test/a?b=1", "login.example.test"),
        ("http://bank.test:8080/x", "bank.test"),
        ("www.bank.test/x", "www.bank.test"),
        ("WIFI:S:home;T:WPA;P:secret;;", None),
        ("javascript:alert(1)", None),
        ("https://", None),
        ("just some text", None),
    ],
)
def test_web_link_host(payload: str, expected: str | None) -> None:
    assert web_link_host(payload) == expected


def test_qr_link_hosts_dedupes_in_order() -> None:
    payloads = [
        "https://a.example.test/one",
        "WIFI:S:home;;",
        "https://A.example.test/two",
        "https://b.example.test/",
    ]

    assert qr_link_hosts(payloads) == ["a.example.test", "b.example.test"]


def test_malicious_qr_domain_is_critical() -> None:
    assessment = qr_link_assessment("bad.example.test", {"malicious": 3, "suspicious": 0})

    assert assessment["risk_score"] == 80
    assert assessment["risk_level"] == "critical"
    assert "bad.example.test" in assessment["assessment"]


def test_unverified_qr_domain_has_no_confidence() -> None:
    assessment = qr_link_assessment("unknown.example.test", None)

    assert assessment["risk_score"] is None
    assert assessment["confidence"] == 0


def test_merge_keeps_highest_score_and_lowest_confidence() -> None:
    message = {
        "risk_score": 20,
        "risk_level": "low",
        "confidence": 90,
        "indicators": [],
        "assessment": "The text looks normal.",
        "recommended_actions": ["Verify the sender."],
    }
    link = {
        "risk_score": 80,
        "risk_level": "critical",
        "confidence": 80,
        "indicators": [{"type": "domain"}],
        "assessment": "The domain is malicious.",
        "recommended_actions": ["Do not open the link.", "Verify the sender."],
    }

    merged = merge_assessments([message, link])

    assert merged["risk_score"] == 80
    assert merged["risk_level"] == "critical"
    assert merged["confidence"] == 80
    assert merged["indicators"] == [{"type": "domain"}]
    assert merged["recommended_actions"] == ["Verify the sender.", "Do not open the link."]


def test_merge_with_unverified_link_drops_confidence() -> None:
    message = {
        "risk_score": 20,
        "risk_level": "low",
        "confidence": 90,
        "indicators": [],
        "assessment": "The text looks normal.",
        "recommended_actions": [],
    }
    unverified = qr_link_assessment("unknown.example.test", None)

    merged = merge_assessments([message, unverified])

    assert merged["risk_score"] == 20
    assert merged["confidence"] == 0


def test_download_assessment_still_reports_clean_domain() -> None:
    assert download_assessment("ok.example.test", {"malicious": 0, "suspicious": 0})[
        "risk_level"
    ] == "low"


def test_preprocess_collects_qr_payload_without_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attachments, "_ocr_image", lambda image: "")
    png = _qr_png("https://login.example.test/reset")
    content = types.Content(
        role="user",
        parts=[
            types.Part(
                inline_data=types.Blob(
                    mime_type="image/png",
                    data=png,
                    display_name="scan.png",
                )
            )
        ],
    )
    context = SimpleNamespace(
        user_content=None,
        invocation_id="inv-1",
        artifact_service=None,
        session=SimpleNamespace(events=[]),
    )
    qr_sink: list[str] = []

    prepared = asyncio.run(
        attachments.preprocess_message_content(content, context, qr_sink=qr_sink)
    )

    assert qr_sink == ["https://login.example.test/reset"]
    text = prepared.parts[-1].text
    assert "QR code payload (decoded, untrusted): https://login.example.test/reset" in text
    assert "[BEGIN UNTRUSTED ATTACHMENT DATA (JSON)]" in text
