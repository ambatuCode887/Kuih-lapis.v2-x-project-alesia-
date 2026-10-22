"""Tests for the incident-response evaluation runner and multilingual behaviour.

Thresholds are regression floors on a synthetic, developer-written dataset, not
claims about real-world accuracy.
"""

from __future__ import annotations

import csv

import pytest

from agents.eval.incident_response import load_cases, run_evaluation, summarize_results
from agents.tools.functions.incident import build_incident_plan


def _none_plan(request, assessment=None, **kwargs):
    return None


def test_dataset_loads_and_validates():
    cases = load_cases()
    assert 40 <= len(cases)
    assert {c["split"] for c in cases} == {"tuned", "challenge"}
    assert {c["language"] for c in cases} >= {"en", "ms", "zh", "mixed"}
    assert len({c["case_id"] for c in cases}) == len(cases)


def test_invalid_dataset_is_rejected(tmp_path):
    bad = tmp_path / "bad.csv"
    with open(bad, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["case_id", "split"])
        writer.writerow(["x", "tuned"])
    with pytest.raises(Exception):
        load_cases(bad)


def test_runner_is_deterministic():
    first = run_evaluation()
    second = run_evaluation()
    assert first["summary"] == second["summary"]
    assert first["dataset_sha256"] == second["dataset_sha256"]


def test_null_baseline_has_zero_recall_and_zero_fpr():
    report = run_evaluation(plan_fn=_none_plan)
    overall = report["summary"]["overall"]
    assert overall["recall"] == 0
    assert overall["false_positive_rate"] == 0
    assert report["summary"]["high_impact_false_negative_rate"] == 1


def test_updated_playbook_beats_null_baseline_and_keeps_floors():
    summary = run_evaluation()["summary"]
    assert summary["error_count"] == 0
    assert summary["overall"]["recall"] >= 0.85
    assert summary["overall"]["false_positive_rate"] <= 0.10
    assert summary["by_split"]["challenge"]["false_positive_rate"] <= 0.10
    assert summary["critical_full_step_coverage_rate"] >= 0.95


def test_summary_reports_each_language_and_category():
    summary = run_evaluation()["summary"]
    assert {"en", "ms", "zh", "mixed"} <= set(summary["by_language"])
    assert "money_sent" in summary["by_category"]
    assert "none" in summary["by_category"]


@pytest.mark.parametrize(
    "text,kind",
    [
        ("I transferred RM3000 to a fake police officer.", "money_sent"),
        ("Saya sudah transfer RM3000 kepada penipu.", "money_sent"),
        ("我已经转账两千块给骗子。", "money_sent"),
    ],
)
def test_money_loss_detected_in_each_language(text, kind):
    plan = build_incident_plan(text)
    assert plan is not None and plan.severity == "critical"
    assert kind in {s.kind for s in plan.signals}


@pytest.mark.parametrize(
    "text",
    [
        "I have not transferred anything, is this a scam?",
        "Saya belum bayar apa-apa, cuma nak tanya ini scam ke tak.",
        "我没有转账，只是想问这是不是诈骗短信。",
        'The message said "please transfer RM500 now" but I ignored it.',
        "My friend transferred RM5000 to a scammer, what should he do?",
    ],
)
def test_negated_quoted_or_third_party_does_not_open_incident(text):
    assert build_incident_plan(text) is None


def test_chinese_and_malay_plans_render_localised_and_use_official_channels_only():
    zh = build_incident_plan("我已经转账两千块给骗子。").render_markdown()
    ms = build_incident_plan("Saya sudah transfer RM3000 kepada penipu.").render_markdown()
    for text in (zh, ms):
        assert "997" in text
        assert "semakmule.rmp.gov.my" in text
    assert any("一" <= ch <= "鿿" for ch in zh)
    assert "wang" in ms.lower() or "bank" in ms.lower()


def test_summarize_handles_empty_input():
    summary = summarize_results([], [])
    assert summary["case_count"] == 0
