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
