from agents.tools.agents.url_check.domain_check import detection_counts, domain_from_request


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
