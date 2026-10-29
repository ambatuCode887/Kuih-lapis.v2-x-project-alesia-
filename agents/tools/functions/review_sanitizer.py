"""Remove sensitive values before unanswered questions leave the application."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_MALAYSIAN_ID = re.compile(r"\b\d{6}[- ]?\d{2}[- ]?\d{4}\b")
_PAYMENT_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{6,}\d)(?!\w)")
_TOKEN = re.compile(
    r"\b(?:sk-[A-Z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b"
)
_URL = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)

_SENSITIVE_WORD = re.compile(
    r"(?<!\w)(?:"
    r"fuck(?:ing|ed|er|s)?|shit(?:ty|ting|s)?|bitch(?:es|y)?|"
    r"cunt(?:s)?|asshole(?:s)?|bastard(?:s)?|dick(?:head|s)?|"
    r"whore(?:s)?|slut(?:s)?|"
    r"n[\W_]*[i1][\W_]*g[\W_]*[g9][\W_]*[ae3][\W_]*r"
    r")(?!\w)",
    re.IGNORECASE,
)


def _redact_url(match: re.Match[str]) -> str:
    value = match.group(0)
    trailing = ""
    while value and value[-1] in ".,!?;:)":
        trailing = value[-1] + trailing
        value = value[:-1]
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "[REDACTED_URL]" + trailing
    if parsed.query or parsed.fragment:
        value = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        value += "[REDACTED_QUERY]"
    return value + trailing


def sanitize_review_text(value: str) -> str:
    """Redact common PII, credentials, private URL parameters, and slurs."""
    text = str(value or "")
    text = _URL.sub(_redact_url, text)
    text = _TOKEN.sub("[REDACTED_TOKEN]", text)
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _MALAYSIAN_ID.sub("[REDACTED_ID]", text)
    text = _PAYMENT_CARD.sub("[REDACTED_PAYMENT_NUMBER]", text)
    text = _PHONE.sub("[REDACTED_PHONE]", text)
    return _SENSITIVE_WORD.sub("[REDACTED_SENSITIVE_LANGUAGE]", text)
