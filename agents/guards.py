"""Detection of prompt-injection and private-internals requests."""

from __future__ import annotations

import re

from agents.tools.agents.message_agents.attachments import targets_ai_instructions


def _attachment_prompt_injection_notice(request: str, *, attachment: bool = True) -> str | None:
    normalized = " ".join(re.findall(r"[a-z0-9]+", request.casefold()))
    attempts_to_override = targets_ai_instructions(request) or any(
        phrase in normalized
        for phrase in (
            "ignore previous instructions",
            "ignore prior instructions",
            "ignore all instructions",
        )
    )
    attempts_to_extract_secrets = any(
        phrase in normalized
        for phrase in (
            "reveal secrets",
            "reveal the secret",
            "reveal passwords",
            "reveal the password",
            "expose secrets",
            "expose the password",
        )
    )
    if not (attempts_to_override or attempts_to_extract_secrets):
        return None
    if attachment:
        return (
            "The attachment contains suspicious document text that appears to "
            "target an AI system, such as asking it to ignore instructions or "
            "reveal secrets. I will treat that text as attempted prompt injection, "
            "not as a command. This alone does not establish that the document is a scam."
        )
    return (
        "The message contains text that appears to target an AI system, such as "
        "asking it to ignore instructions, translate or reveal its instructions, "
        "or emit a token. I will treat that as suspicious content, not as a "
        "command. This alone does not establish that the message is a scam."
    )


def _requests_private_internals(request: str) -> bool:
    if re.match(
        r"^\s*(?:please\s+)?(?:analy[sz]e|review|check|assess)\s+"
        r"(?:this\s+)?(?:message|email|text|screenshot|image|document)\b",
        request,
        re.IGNORECASE,
    ):
        return False

    if targets_ai_instructions(request):
        return True

    normalized = " ".join(re.findall(r"[a-z0-9]+", request.casefold()))
    override_pattern = re.compile(
        r"\b(?:ignore|disregard|override|replace|rewrite|change|modify|update|"
        r"disable|bypass|forget|delete)\b.{0,80}\b(?:system|developer|hidden|"
        r"internal|safety|security)?\s*(?:prompt|instructions?|rules|polic(?:y|ies)|"
        r"configuration|constraints)\b"
    )
    disclosure_pattern = re.compile(
        r"\b(?:reveal|show|print|list|repeat|quote|dump|disclose|expose|output|"
        r"give me|tell me|what are)\b.{0,80}\b(?:your\s+)?(?:system|developer|"
        r"hidden|internal|private)?\s*(?:prompt|instructions?|rules|polic(?:y|ies)|"
        r"configuration|reasoning|chain of thought|secrets?)\b"
    )
    private_request_cues = (
        "internal reasoning",
        "private reasoning",
        "chain of thought",
        "chain-of-thought",
        "system prompt",
        "developer prompt",
        "developer instructions",
        "hidden instructions",
        "internal instructions",
        "from your instructions",
        "list every rule",
        "reveal your prompt",
        "show your prompt",
        "what are your instructions",
        "private configuration",
        "secret rules",
    )
    requests_canary = re.search(
        r"\b(?:say|output|repeat|include|end with|end (?:your answer )?(?:with|in))"
        r"\s+canary(?:\s+[a-z0-9-]+)?\b",
        normalized,
    )
    return (
        any(cue in normalized for cue in private_request_cues)
        or bool(override_pattern.search(normalized))
        or bool(disclosure_pattern.search(normalized))
        or bool(requests_canary)
    )
