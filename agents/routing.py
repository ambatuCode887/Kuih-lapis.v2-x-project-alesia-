"""Deterministic request routing that picks a specialist before any model call."""

from __future__ import annotations

import re

from agents.safety import immediate_safety_notice
from agents.scope import OUT_OF_SCOPE_REPLY
from agents.tools.functions.semantic_route import semantic_knowledge_route

_CYBER_KNOWLEDGE_TERMS = (
    "cybersecurity",
    "cyber security",
    "cyber attack",
    "cyber malicious attack",
    "stay safe online",
    "online safety",
    "protect myself online",
    "safe browsing",
    "browse the internet",
    "online account",
    "hacked",
    "home router",
    "home network",
    "home wi-fi",
    "home wifi",
    "account takeover",
    "taking over my account",
    "clicked on a suspicious link",
    "clicking a suspicious link",
    "after clicking a suspicious link",
    "malware",
    "virus",
    "ransomware",
    "phishing",
    "scam",
    "credential stuffing",
    "password",
    "public wi-fi",
    "public wifi",
    "firewall",
    "encryption",
    "vpn",
    "multi-factor",
    "two-factor",
    "two factor",
    "mfa",
    "data breach",
    "network security",
    "antivirus",
    "spyware",
    "trojan",
    "identity theft",
    "social engineering",
    "hacking",
    "security risk",
    "work laptop",
)
_ANALYSIS_CUES = (
    "analyze this",
    "analyse this",
    "check this",
    "review this",
    "inspect this",
    "classify this",
    "score this",
    "i received",
    "i got this",
    "someone sent me",
    "someone emailed me",
    "this email",
    "this message",
    "this link",
    "this file",
    "is this a scam",
    "is this text a scam",
    "is this phishing",
    "could this be a scam",
    "could this be a phishing",
    "does this look suspicious",
    "does this look like a scam",
)
_URL_ANALYSIS_CUES = (
    "check this domain",
    "check this ip",
    "check this link",
    "check the link",
    "check this url",
    "check the url",
    "malicious link",
    "is this link malicious",
    "is this url malicious",
    "is this domain malicious",
    "is this link safe",
    "is this url safe",
    "analyze this url",
    "analyse this url",
    "url reputation",
    "domain reputation",
    "ip reputation",
    "scan this link",
    "look up this domain",
    "check the reputation",
    "reputation of this domain",
    "is this a suspicious link",
    "is this link suspicious",
    "is this a suspicious url",
    "is this url suspicious",
)
_URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_QUESTION_START = re.compile(
    r"^\s*(?:how|what|why|when|where|which|who|can|could|should|is|are|do|does|did|will|would)\b"
)
_ARTIFACT_REFERENCE = re.compile(
    r"\b(?:this|these|those|message|text|sms|email|link|url|domain|file|attachment|"
    r"screenshot|caller|website)\b"
)
_SITUATIONAL_RISK_TERMS = re.compile(
    r"\b(?:transfer|pay|paid|payment|fee|fees|otp|gift cards?|send money|police|scammer)\b"
)
_MAX_KNOWLEDGE_QUESTION_WORDS = 40
_GIBBERISH_REPLY = (
    "I couldn't make out that message. Could you rephrase it as a cybersecurity question?"
)
_OFF_TOPIC_REPLY = OUT_OF_SCOPE_REPLY
_SECURITY_VOCABULARY = re.compile(
    r"\b(?:cyber\w*|secur\w*|privacy|private|hack\w*|attack\w*|malic\w*|malware|virus\w*|"
    r"phish\w*|scam\w*|fraud\w*|spam\w*|ransom\w*|spyware|trojan\w*|worm\w*|botnet\w*|"
    r"exploit\w*|vulnerab\w*|threat\w*|breach\w*|leak\w*|injection|sql|xss|ddos|honeypot|siem|"
    r"encrypt\w*|decrypt\w*|password\w*|passcode|passphrase|login\w*|account\w*|"
    r"authenticat\w*|mfa|2fa|otp|vpn|firewall\w*|wi-?fi|router|network\w*|internet|online|"
    r"browser|patch\w*|backup\w*|identity|intrusion|incident\w*|forensic\w*|kubernetes|cloud|"
    r"bank\w*|money|pay|payment\w*|fee\w*|parcel|courier|delivery|prize|invoice|transfer\w*|"
    r"gift|verif\w*|suspicious|legit\w*|fake|genuine|real|look|email\w*|sms|text\w*|"
    r"message\w*|link\w*|url\w*|domain\w*|website\w*|malicious|crypto\w*|wallet|device\w*|"
    r"laptop|phone\w*|hacked|safe\w*|protect\w*|credential\w*|stuffing|sensitive|"
    r"dispos\w*|shred\w*|documents?|data|privileged|container\w*|cookie\w*|ssl|tls|https|"
    r"dns|scan\w*)\b"
)
_VOWEL_PATTERN = re.compile(r"[aeiouy]")
_CONSONANT_RUN = re.compile(r"[bcdfghjklmnpqrstvwxz]{5,}")


def should_route_to_retrieval(request: str) -> bool:
    """Return whether a request is a cybersecurity knowledge question."""
    normalized = request.casefold()
    if (
        not normalized.strip()
        or _URL_PATTERN.search(normalized)
        or _IP_PATTERN.search(normalized)
    ):
        return False
    if any(cue in normalized for cue in _ANALYSIS_CUES):
        return False
    return any(term in normalized for term in _CYBER_KNOWLEDGE_TERMS)


def is_knowledge_question(request: str) -> bool:
    """Return whether a question-form request asks general knowledge, not analysis."""
    normalized = request.casefold()
    if (
        not _QUESTION_START.match(normalized)
        or len(normalized.split()) > _MAX_KNOWLEDGE_QUESTION_WORDS
        or _URL_PATTERN.search(normalized)
        or _IP_PATTERN.search(normalized)
        or any(cue in normalized for cue in (*_ANALYSIS_CUES, *_URL_ANALYSIS_CUES))
    ):
        return False
    return not (
        _ARTIFACT_REFERENCE.search(normalized)
        or _SITUATIONAL_RISK_TERMS.search(normalized)
    )


def _is_gibberish(request: str) -> bool:
    """Return whether a request has too few pronounceable words to be a real question."""
    if any(ord(char) > 127 for char in request):
        return False
    words = re.findall(r"[a-z]+", request.casefold())
    if not words:
        return bool(request.strip())
    word_like = [
        word
        for word in words
        if _VOWEL_PATTERN.search(word) and not _CONSONANT_RUN.search(word)
    ]
    return len(word_like) / len(words) < 0.5


def _is_off_topic(request: str) -> bool:
    """Return whether a question-form request has no security or scam vocabulary."""
    normalized = request.casefold()
    if not _QUESTION_START.match(normalized) or _SECURITY_VOCABULARY.search(normalized):
        return False
    return not any(term in normalized for term in _CYBER_KNOWLEDGE_TERMS)


def _unsupported_request_reply(request: str, *, attachment_present: bool, state) -> str | None:
    """Return a refusal for gibberish or off-topic text, or None to continue."""
    if attachment_present or _URL_PATTERN.search(request) or _IP_PATTERN.search(request):
        return None
    if _is_gibberish(request):
        return _GIBBERISH_REPLY
    if state.get("knowledge_memory"):
        return None
    if _is_off_topic(request):
        return _OFF_TOPIC_REPLY
    return None


def route_request_to_agent(
    request: str,
    attachment_present: bool = False,
    user_request: str | None = None,
) -> str:
    """Choose a specialist directly, without an LLM orchestration layer."""
    if attachment_present:
        intent = (user_request or request).casefold()
        if (
            _URL_PATTERN.search(intent)
            or _IP_PATTERN.search(intent)
            or any(cue in intent for cue in _URL_ANALYSIS_CUES)
        ):
            return "url_check_agent"
        refers_to_attachment = any(
            term in intent for term in ("screenshot", "image", "photo", "attachment")
        )
        asks_about_scam = any(
            term in intent for term in ("scam", "suspicious", "phishing", "fraud")
        )
        if any(cue in intent for cue in _ANALYSIS_CUES) or (
            refers_to_attachment and asks_about_scam
        ):
            return "message_agent"
        if should_route_to_retrieval(intent):
            return "retrieval_agent"
        return "message_agent"
    if immediate_safety_notice(request):
        return "message_agent"
    normalized = request.casefold()
    if _URL_PATTERN.search(normalized) or _IP_PATTERN.search(normalized) or any(
        cue in normalized for cue in _URL_ANALYSIS_CUES
    ):
        return "url_check_agent"
    if should_route_to_retrieval(request):
        return "retrieval_agent"
    if is_knowledge_question(request):
        return "retrieval_agent"
    return semantic_knowledge_route(request)
