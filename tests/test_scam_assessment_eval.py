import csv
from pathlib import Path

import pytest

from agents.eval.scam_assessment import (
    load_reviewed_cases,
    score_result,
    summarize_results,
    validate_assessment,
)


def test_scam_assessment_cases_have_valid_reviewed_labels() -> None:
    dataset_path = (
        Path(__file__).resolve().parents[1]
        / "agents"
        / "eval"
        / "datasets"
        / "scam_assessment_cases.csv"
    )
    with dataset_path.open(newline="", encoding="utf-8") as handle:
        cases = list(csv.DictReader(handle))

    allowed_risk_levels = {
        "low",
        "moderate",
        "high",
        "critical",
        "insufficient_information",
    }
    allowed_indicators = {
        "urgency",
        "impersonation",
        "credential_request",
        "payment_request",
        "secrecy",
        "suspicious_link",
        "other",
    }

    assert len(cases) >= 10
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert {
        "low",
        "moderate",
        "high",
        "critical",
        "insufficient_information",
    }.issubset({case["expected_risk_level"] for case in cases})

    for case in cases:
        indicators = {
            item for item in case["expected_indicators"].split("|") if item
        }
        assert case["user_request"].strip()
        assert case["expected_risk_level"] in allowed_risk_levels
        assert indicators.issubset(allowed_indicators)
        assert case["clarification_expected"] in {"true", "false"}
        assert case["review_status"] == "reviewed"
        assert case["review_notes"].strip()


def test_message_assessment_prompt_preserves_image_uncertainty_and_weak_cues() -> None:
    prompt_path = (
        Path(__file__).resolve().parents[1]
        / "agents"
        / "tools"
        / "agents"
        / "message_agents"
        / "prompt.md"
    )
    prompt = prompt_path.read_text(encoding="utf-8")

    assert "Do not treat incomplete or sparse extracted text from an image as evidence that it is safe" in prompt
    assert "Treat requests for deposits, delivery/processing fees, off-platform payment" in prompt
    assert "Use `moderate` (25-49) when such a cue is plausible but not conclusive" in prompt
    assert "Use `low` only when the supplied evidence is complete enough to assess" in prompt


def test_reviewed_case_loader_rejects_draft_cases(tmp_path) -> None:
    dataset = tmp_path / "cases.csv"
    dataset.write_text(
        "case_id,review_status\none,draft\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Every case must be reviewed"):
        load_reviewed_cases(dataset)


def test_assessment_scorer_reports_expected_indicator_and_routing_matches() -> None:
    case = {
        "case_id": "scam-test",
        "expected_risk_level": "high",
        "expected_indicators": "urgency|credential_request",
        "clarification_expected": "false",
    }
    assessment = {
        "risk_score": 60,
        "risk_level": "high",
        "confidence": 80,
        "indicators": [
            {"type": "urgency", "evidence": "Act now", "reason": "Pressure."},
            {
                "type": "credential_request",
                "evidence": "Send your code",
                "reason": "Requests a verification code.",
            },
        ],
        "assessment": "The message uses urgency and requests a code.",
        "recommended_actions": ["Verify through a trusted channel."],
    }

    result = score_result(case, assessment, "model response")
    summary = summarize_results([result])

    assert result["schema_valid"]
    assert result["risk_level_match"]
    assert result["expected_indicator_recall"] == 1.0
    assert result["clarification_match"]
    assert summary["valid_schema_rate"] == 1.0
    assert summary["risk_level_exact_match_rate"] == 1.0


def test_assessment_validation_separates_score_consistency_from_schema() -> None:
    assessment = {
        "risk_score": 80,
        "risk_level": "high",
        "confidence": 75,
        "indicators": [],
        "assessment": "High risk.",
        "recommended_actions": [],
    }

    validation = validate_assessment(assessment)
    assert validation["schema_errors"] == []
    assert "risk_score does not match the documented risk_level band" in (
        validation["consistency_errors"]
    )