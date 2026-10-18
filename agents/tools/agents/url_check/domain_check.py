"""Deterministic VirusTotal domain check that does not depend on LLM tool choice."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools.tool_context import ToolContext

from agents.tools.agents.url_check.agent import virustotal_toolset

logger = logging.getLogger(__name__)

_DOMAIN_CHECK_PATTERN = re.compile(r"^\s*Check this domain:\s*([A-Za-z0-9.-]+)\s*$")


def domain_from_request(request: str) -> str | None:
    """Return the host from a `Check this domain: <host>` request, else None."""
    match = _DOMAIN_CHECK_PATTERN.match(request)
    return match.group(1).lower() if match else None


_DOWNLOAD_CHECK_PATTERN = re.compile(r"^\s*Check download source:\s*([A-Za-z0-9.-]+)\s*$")


def download_source_from_request(request: str) -> str | None:
    """Return the host from a `Check download source: <host>` request, else None."""
    match = _DOWNLOAD_CHECK_PATTERN.match(request)
    return match.group(1).lower() if match else None


def download_assessment(domain: str, counts: dict[str, int] | None) -> dict[str, Any]:
    """Build the url_check assessment for a download source from VirusTotal counts."""
    if counts is None:
        return {
            "risk_score": None,
            "risk_level": "insufficient_information",
            "confidence": 0,
            "indicators": [
                {"indicator": domain, "verdict": "unknown", "evidence": "No VirusTotal report was returned."}
            ],
            "assessment": f"The reputation of {domain} could not be verified.",
            "recommended_actions": ["Verify the download source before opening the file."],
            "limitations": ["The VirusTotal lookup failed or returned no report."],
        }
    malicious = counts["malicious"]
    suspicious = counts["suspicious"]
    if malicious:
        verdict, score, level = "malicious", 80, "critical"
        summary = f"VirusTotal reports {domain} as malicious ({malicious} engine(s))."
    elif suspicious:
        verdict, score, level = "suspicious", 50, "high"
        summary = f"VirusTotal reports {suspicious} suspicious detection(s) for {domain}."
    else:
        verdict, score, level = "clean", 0, "low"
        summary = (
            f"VirusTotal reports no malicious or suspicious detections for {domain}. "
            "That does not prove it is safe."
        )
    return {
        "risk_score": score,
        "risk_level": level,
        "confidence": 80,
        "indicators": [
            {
                "indicator": domain,
                "verdict": verdict,
                "evidence": f"{malicious} malicious, {suspicious} suspicious detections.",
            }
        ],
        "assessment": summary,
        "recommended_actions": [] if verdict == "clean" else ["Do not open the file if the source looks unexpected."],
        "limitations": [],
    }


def detection_counts(result: Any) -> dict[str, int] | None:
    """Read malicious and suspicious counts from a get_domain_report tool result."""
    if not isinstance(result, dict) or "error" in result:
        return None
    report = result.get("structuredContent")
    if not isinstance(report, dict):
        content = result.get("content") or []
        text = content[0].get("text") if content and isinstance(content[0], dict) else None
        if not text:
            return None
        try:
            report = json.loads(text)
        except json.JSONDecodeError:
            return None
    stats = ((report or {}).get("data") or {}).get("last_analysis_stats") or {}
    malicious = stats.get("malicious")
    suspicious = stats.get("suspicious")
    if not isinstance(malicious, int) or not isinstance(suspicious, int):
        return None
    return {"malicious": malicious, "suspicious": suspicious}


async def check_domain_counts(domain: str, ctx: InvocationContext) -> dict[str, int] | None:
    """Call VirusTotal get_domain_report directly. Returns None on any failure."""
    try:
        tools = await virustotal_toolset().get_tools()
        tool = next((t for t in tools if t.name == "get_domain_report"), None)
        if tool is None:
            return None
        result = await tool.run_async(
            args={"domain": domain},
            tool_context=ToolContext(ctx),
        )
    except Exception:
        logger.exception("Deterministic domain check failed for %s.", domain)
        return None
    return detection_counts(result)
