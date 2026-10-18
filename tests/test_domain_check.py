from agents.tools.agents.url_check.domain_check import (
    detection_counts,
    domain_from_request,
    download_assessment,
    download_source_from_request,
)


def test_domain_from_request_accepts_download_guard_format():
    assert domain_from_request("Check this domain: Speed.Cloudflare.com") == "speed.cloudflare.com"


def test_domain_from_request_rejects_other_text():
    assert domain_from_request("Check this domain: example.com and more") is None
    assert domain_from_request("is example.com safe?") is None


def test_detection_counts_reads_structured_content():
    result = {"structuredContent": {"data": {"last_analysis_stats": {"malicious": 0, "suspicious": 2}}}}
    assert detection_counts(result) == {"malicious": 0, "suspicious": 2}


def test_detection_counts_parses_text_content():
    text = '{"data": {"last_analysis_stats": {"malicious": 3, "suspicious": 0}}}'
    assert detection_counts({"content": [{"type": "text", "text": text}]}) == {
        "malicious": 3,
        "suspicious": 0,
    }


def test_detection_counts_returns_none_on_error_or_missing_stats():
    assert detection_counts({"error": "MCP tool execution failed"}) is None
    assert detection_counts({"content": [{"type": "text", "text": "not json"}]}) is None
    assert detection_counts({"structuredContent": {"data": {}}}) is None
    assert detection_counts(None) is None


def test_download_source_accepts_download_check_format_only():
    assert download_source_from_request("Check download source: Speed.Cloudflare.com") == "speed.cloudflare.com"
    assert download_source_from_request("Check this domain: example.com") is None


def test_download_assessment_maps_counts_to_verdicts():
    malicious = download_assessment("example.com", {"malicious": 3, "suspicious": 0})
    assert malicious["indicators"][0]["verdict"] == "malicious"
    assert malicious["risk_level"] == "critical"

    suspicious = download_assessment("example.com", {"malicious": 0, "suspicious": 2})
    assert suspicious["indicators"][0]["verdict"] == "suspicious"

    clean = download_assessment("example.com", {"malicious": 0, "suspicious": 0})
    assert clean["indicators"][0]["verdict"] == "clean"
    assert clean["risk_level"] == "low"


def test_download_assessment_is_unknown_without_counts():
    unknown = download_assessment("example.com", None)
    assert unknown["risk_level"] == "insufficient_information"
    assert unknown["indicators"][0]["verdict"] == "unknown"
