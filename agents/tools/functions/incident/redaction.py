"""Deterministic redaction of personal data and secrets before text is stored or logged.

Pure, offline, no dependencies. It is a best-effort safety net, not a guarantee:
regex redaction cannot catch every identifier (names, addresses, free-text
account descriptions), so callers must still treat redacted text as sensitive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Redaction:
    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        n = int(ch)
        if alt:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
        alt = not alt
    return total % 10 == 0


# Order matters: most specific first so later patterns do not re-match placeholders.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)")),
    ("jwt", re.compile(r"\beyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}\b")),
    (
        "api_key",
        re.compile(
            r"\b(?:sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|"
            r"xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})\b"
        ),
    ),
    ("url_credentials", re.compile(r"(?i)\b(https?://)[^\s/@:]+:[^\s/@]+@")),
    (
        "secret_assignment",
        re.compile(r"(?i)\b(password|passwd|pwd|pin|token|secret|api[_-]?key|kata\s*laluan|密码)\s*[:=]\s*\S+"),
    ),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("nric", re.compile(r"\b\d{6}-?\d{2}-?\d{4}\b")),
    (
        "otp",
        re.compile(
            r"(?i)\b(?:otp|tac|code|kod|verification)\b[^\d\n]{0,20}\b\d{4,8}\b|(?:验证码|驗證碼)[^\d\n]{0,6}\d{4,8}"
        ),
    ),
    ("phone", re.compile(r"(?<![\d-])(?:\+?60[ -]?|0)1\d(?:[ -]?\d){7,8}(?!\d)")),
)
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_ACCOUNT = re.compile(r"(?<!\d)\d{10,16}(?!\d)")


def redact(text: str) -> Redaction:
    """Replace sensitive substrings with ``[REDACTED:<kind>]`` markers."""
    counts: dict[str, int] = {}
    out = text or ""

    def sub(kind: str, pattern: re.Pattern[str], repl=None) -> None:
        nonlocal out
        out, n = pattern.subn(repl or f"[REDACTED:{kind}]", out)
        if n:
            counts[kind] = counts.get(kind, 0) + n

    for kind, pattern in _PATTERNS:
        if kind == "url_credentials":
            sub(kind, pattern, r"\1[REDACTED:url_credentials]@")
        elif kind == "secret_assignment":
            sub(kind, pattern, lambda m: f"{m.group(1)}=[REDACTED:secret]")
        else:
            sub(kind, pattern)

    def card(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19 and _luhn(digits):
            counts["card_number"] = counts.get("card_number", 0) + 1
            return "[REDACTED:card_number]"
        return match.group(0)

    out = _CARD.sub(card, out)

    def account(match: re.Match[str]) -> str:
        counts["account_number"] = counts.get("account_number", 0) + 1
        return "[REDACTED:account_number]"

    out = _ACCOUNT.sub(account, out)
    return Redaction(out, counts)
