"""Deterministic scam-victim incident-response playbook (Jira KAN-44 / KAN-98).

Given what a user says they already did (paid, shared a code, installed an app
...), build an ordered, explainable list of containment and evidence steps.

Design rules
------------
* Pure and deterministic: no LLM, no network, no file or process side effects,
  no third-party dependencies. The same input always gives the same plan.
* Advice only. Nothing here contacts a bank, the police or anyone else, and the
  rendered text says so. Every step is something the *user* does.
* Only fixed, official channels are ever named (see ``OFFICIAL_CHANNELS``).
  Phone numbers and URLs found in the user's text or in a scam message are
  never echoed, and the plan tells the user not to use them.
* The user's wording is never quoted back. "Why" lines are templated, so
  attacker-controlled text cannot reach the output.
* Classification uses clause-level patterns (negation and hedging aware) plus
  context: the scam wording of the same message and, optionally, the existing
  message/URL assessment. The assessment can only make the plan *more*
  cautious; it can never remove a step or lower a severity that the user's own
  words established, and it can never create an incident on its own.
* Ambiguity fails safe: unclear or hedged statements give a precautionary plan
  with conditional steps and the questions that would resolve it.

Ownership note: Jira could not be read when this was written. KAN-44 is
assigned to Yi; KAN-86 (defensive recommendations), KAN-94 (case management /
audit trail) and KAN-98 (victim-state assessment) were unassigned "To Do" in a
screenshot. This module covers the recommendation and victim-state parts only.
It does not implement case storage, an audit trail, calibration (KAN-97) or
the approval workflow (KAN-93); confirm ownership before extending it.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from .lexicon import detect_language, detect_signals, has_scam_context
from .messages import SUPPORTED_LANGUAGES, Translator

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

SEVERITY_ORDER = ("precautionary", "moderate", "high", "critical")  # rank = index + 1
_TIER_ORDER = {"now": 0, "today": 1, "follow_up": 2}
_TIER_TITLES = {
    "now": "Do these now",
    "today": "Later today",
    "follow_up": "Over the next few days",
}

# Mirrors coordinator_agents.agent.CONFIDENCE_THRESHOLD without importing ADK.
ASSESSMENT_CONFIDENCE_THRESHOLD = 60
_MAX_TEXT_CHARS = 4000


@dataclass(frozen=True)
class Channel:
    name: str
    how: str


# The only contacts the playbook will ever name. Sourced from the project's
# existing prompts (message_agents / verification_agents) and Jira KAN-44.
OFFICIAL_CHANNELS: dict[str, Channel] = {
    "bank": Channel(
        "Your bank's official fraud line",
        "use the number on the back of your card or inside the bank's official app",
    ),
    "nsrc": Channel(
        "National Scam Response Centre (NSRC), Malaysia",
        "dial 997",
    ),
    "police": Channel(
        "Royal Malaysia Police (PDRM)",
        "make a report at a police station; keep the report number",
    ),
    "nfcc": Channel(
        "National Fraud Command Centre (NFCC), Malaysia",
        "https://nfcc.jpm.gov.my/index.php/en/",
    ),
    "semak_mule": Channel(
        "Semak Mule (PDRM), Malaysia",
        "open https://semakmule.rmp.gov.my/ yourself to check a recipient account; "
        "do not paste account numbers into chat",
    ),
}

# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Signal:
    kind: str  # see _BASE_RANK
    status: str  # "confirmed" | "possible"


@dataclass(frozen=True)
class Step:
    id: str
    tier: str  # "now" | "today" | "follow_up"
    action: str
    why: str
    triggered_by: tuple[str, ...]
    conditional: bool = False
    channel: str | None = None


@dataclass(frozen=True)
class IncidentPlan:
    severity: str
    headline: str
    signals: tuple[Signal, ...]
    steps: tuple[Step, ...]
    questions: tuple[str, ...]
    channels: tuple[str, ...]
    assessment_used: bool = False
    untrusted_contact_seen: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)
    language: str = "en"
    headline_kind: str = ""

    @property
    def severity_rank(self) -> int:
        return SEVERITY_ORDER.index(self.severity) + 1

    @property
    def urgent_notice(self) -> str:
        tr = Translator(self.language)
        return tr.ui("urgent_critical" if self.severity == "critical" else "urgent_generic")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"severity_rank": self.severity_rank}

    def render_markdown(self) -> str:
        tr = Translator(self.language)
        lines = [
            tr.ui("title", headline=tr.headline(self.headline_kind, self.headline)),
            tr.ui("severity_line", severity=tr.severity(self.severity)),
            "",
        ]
        number = 0
        for tier in ("now", "today", "follow_up"):
            tier_steps = [s for s in self.steps if s.tier == tier]
            if not tier_steps:
                continue
            lines.append(f"**{tr.ui('tier_' + tier)}**")
            for step in tier_steps:
                number += 1
                action, why = tr.step(step.id, step.action, step.why, step.conditional)
                prefix = tr.ui("conditional") if step.conditional else ""
                lines.append(f"{number}. {prefix}{action}")
                lines.append(f"   - *{tr.ui('why')}:* {why}")
            lines.append("")
        if self.channels:
            lines.append(f"**{tr.ui('channels')}**")
            for key in self.channels:
                channel = OFFICIAL_CHANNELS[key]
                name, how = tr.channel(key, channel.name, channel.how)
                lines.append(f"- {name}: {how}")
            lines.append("")
        if self.questions:
            lines.append(f"**{tr.ui('questions')}**")
            lines.extend(f"- {tr.question(question)}" for question in self.questions)
            lines.append("")
        if self.untrusted_contact_seen:
            lines.append(tr.ui("untrusted"))
        if self.assessment_used:
            lines.append(f"_{tr.ui('analysis_note')}_")
        for note in self.notes:
            lines.append(f"_{note}_")
        return "\n".join(lines).strip()


# --------------------------------------------------------------------------
# Detection (patterns live in lexicon.py)
# --------------------------------------------------------------------------

_BASE_RANK = {
    "money_sent": 4,
    "financial_credentials": 4,
    "other_credentials": 3,
    "data_entered_on_site": 3,
    "remote_access": 3,
    "app_installed": 3,
    "identity_documents": 3,
    "recovery_scam": 3,
    "unspecified_victim": 2,
    "link_interaction": 2,
}

_PHONE = re.compile(r"\+?\d[\d\s\-]{7,}\d")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


@dataclass(frozen=True)
class _AssessmentContext:
    used: bool
    high_risk: bool


def _read_assessment(assessment: Any) -> _AssessmentContext:
    """Read only validated, fixed fields from an (untrusted) model assessment."""
    if not isinstance(assessment, Mapping):
        return _AssessmentContext(False, False)
    level = assessment.get("risk_level")
    confidence = assessment.get("confidence")
    if (
        not isinstance(level, str)
        or isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0 <= confidence <= 100
    ):
        return _AssessmentContext(False, False)
    high = level in {"high", "critical"} and confidence >= ASSESSMENT_CONFIDENCE_THRESHOLD
    return _AssessmentContext(True, high)


# --------------------------------------------------------------------------
# Step catalogue
# --------------------------------------------------------------------------

_HEADLINES = {
    "money_sent": "money may have left your account",
    "financial_credentials": "banking details or a one-time code may be exposed",
    "other_credentials": "a password or login may be exposed",
    "data_entered_on_site": "you may have entered details on a fake page",
    "remote_access": "someone may have access to your device",
    "app_installed": "a suspicious app may be on your device",
    "identity_documents": "your identity documents may be exposed",
    "link_interaction": "you opened a suspicious link",
    "unspecified_victim": "you think you may have been scammed",
    "recovery_scam": "someone is offering to recover your money for a fee",
}

_WHY = {
    "money_sent": "you said money was sent or taken",
    "financial_credentials": "you said a code, PIN or banking/card detail was shared",
    "other_credentials": "you said a password or login was shared",
    "data_entered_on_site": "you said details were entered on a page or form",
    "remote_access": "you said remote access or a remote-control tool was involved",
    "app_installed": "you said an app or file was installed",
    "identity_documents": "you said ID documents or a selfie were shared",
    "link_interaction": "you said you opened a link",
    "unspecified_victim": "you said you may have been scammed but not what happened",
    "recovery_scam": "you said someone offered to recover your money for a fee",
}


def _step(id_: str, tier: str, action: str, why: str, *kinds: str, conditional: bool = False,
          channel: str | None = None) -> Step:
    return Step(id_, tier, action, why, tuple(kinds), conditional, channel)


def _catalogue(kinds: dict[str, str], escalated: bool) -> list[Step]:
    """Build candidate steps. ``escalated``: ambiguity resolved toward caution."""
    steps: list[Step] = []
    money = "money_sent" in kinds
    fin = "financial_credentials" in kinds
    other = "other_credentials" in kinds or "data_entered_on_site" in kinds
    remote = "remote_access" in kinds or "app_installed" in kinds
    ident = "identity_documents" in kinds
    link = "link_interaction" in kinds
    vague = "unspecified_victim" in kinds
    recovery = "recovery_scam" in kinds

    def is_conditional(*ks: str) -> bool:
        # A vague "I got scammed" says nothing about what was lost.
        confirmed = any(
            kinds.get(k) == "confirmed" for k in ks if k != "unspecified_victim"
        )
        return not confirmed and not escalated

    if remote:
        ks = [k for k in ("remote_access", "app_installed") if k in kinds]
        steps.append(_step(
            "disconnect_device", "now",
            "Turn off Wi-Fi and mobile data on the affected device, and close or "
            "uninstall the remote-control or unknown app from Settings. Do the next "
            "steps from a different, clean device or phone line if you can.",
            "Cutting the connection stops anyone watching the screen or approving "
            "transactions while you recover; " + _WHY[ks[0]] + ".",
            *ks, conditional=is_conditional(*ks)))

    if money or fin or vague:
        ks = [k for k in ("money_sent", "financial_credentials", "unspecified_victim") if k in kinds]
        hard = [k for k in ks if k != "unspecified_victim"]
        cond = is_conditional(*(hard or ks))
        steps.append(_step(
            "call_bank", "now",
            "Call your bank's official fraud line (number from your card or the "
            "bank's official app, not from any message) and ask them to block "
            "your card/online banking, and to stop or trace the transfer"
            + (" if any money left your account." if cond else "."),
            "Speed matters: banks can sometimes hold or trace a transfer only "
            "shortly after it is made; " + _WHY[ks[0]] + ".",
            *ks, conditional=cond, channel="bank"))
        steps.append(_step(
            "call_nsrc", "now",
            "Report to the National Scam Response Centre by dialling 997 (Malaysia).",
            "NSRC coordinates with banks on suspected scam transfers; "
            + _WHY[ks[0]] + ".",
            *ks, conditional=cond, channel="nsrc"))

    if money or fin or other or vague:
        ks = [k for k in ("financial_credentials", "other_credentials", "data_entered_on_site") if k in kinds]
        if ks:
            steps.append(_step(
                "change_credentials", "now" if (fin or other) else "today",
                "Change the exposed passwords through the official website or app "
                "(type the address yourself), starting with your email and banking. "
                "Sign out of all other sessions/devices and turn on multi-factor "
                "authentication. Change any other account that reuses that password.",
                "A shared password or code lets the scammer log in until it is "
                "changed and old sessions are revoked; " + _WHY[ks[0]] + ".",
                *ks, conditional=is_conditional(*ks)))
            steps.append(_step(
                "never_share_otp", "today",
                "Do not give anyone your OTP, PIN or password again, even someone "
                "claiming to be helping you recover your money.",
                "Follow-up callers often pose as recovery or bank staff to get a "
                "second set of codes.",
                *ks))

    if link and not (fin or other):
        steps.append(_step(
            "contain_link", "now",
            "Close the page, do not enter any details, and do not reopen the link. "
            "If you did type anything, tell me what kind (never the actual values) "
            "and treat it as shared credentials.",
            "Opening a link alone is lower risk than entering data, but it can "
            "lead to fake login pages or downloads; " + _WHY["link_interaction"] + ".",
            "link_interaction"))
        steps.append(_step(
            "scan_device", "today",
            "Run a scan with an up-to-date security app and review recently "
            "installed apps and downloads for anything you do not recognise.",
            "A malicious page can try to download software without being obvious.",
            "link_interaction"))

    if remote:
        ks = [k for k in ("remote_access", "app_installed") if k in kinds]
        steps.append(_step(
            "clean_device", "today",
            "Review installed apps, device-administrator and accessibility "
            "permissions and remove anything you did not install on purpose. If you "
            "cannot remove it, back up your photos/documents and factory-reset the device.",
            "Some malicious apps hide or re-install themselves, so removal needs "
            "checking afterwards.",
            *ks, conditional=is_conditional(*ks)))

    if ident:
        steps.append(_step(
            "identity_watch", "today",
            "Tell your bank, watch for new accounts, loans or SIM registrations in "
            "your name, and check your credit report (for example CCRIS via Bank "
            "Negara Malaysia, or a credit bureau you trust) for entries you do not recognise.",
            "A copy of your ID or selfie can be used to open accounts or pass "
            "identity checks; " + _WHY["identity_documents"] + ".",
            "identity_documents", conditional=is_conditional("identity_documents")))

    if recovery:
        steps.append(_step(
            "reject_recovery_offer", "now",
            "Do not pay anyone who offers to recover your money for a fee, and do not "
            "share your bank or ID details with them. Verify any recovery help only "
            "through your bank or NSRC (997), using contact details you find yourself.",
            "Recovery scams target people who have already lost money; official "
            "reporting channels do not require you to pay for your report to be taken.",
            "recovery_scam", channel="nsrc"))

    # Evidence and reporting apply to every incident.
    all_kinds = tuple(kinds)
    steps.append(_step(
        "preserve_evidence", "now" if (money or fin) else "today",
        "Before blocking or deleting anything, take screenshots of the chat, "
        "messages, caller number, website address and payment receipts, and note "
        "dates, times, amounts and recipient account details. Do not reply to or "
        "confront the scammer.",
        "Banks and the police need this to trace and report the case, and it is "
        "easy to lose once a chat is deleted.",
        *all_kinds))
    if money or fin or vague or recovery:
        steps.append(_step(
            "police_report", "today",
            "Make a police report and keep the report number and a copy of your receipts.",
            "A police report is usually needed for bank investigations; "
            + _WHY[next(iter(kinds))] + ".",
            *all_kinds, conditional=is_conditional(*all_kinds), channel="police"))
        steps.append(_step(
            "no_more_payments", "now",
            "Do not send any more money, including 'fees', 'taxes' or 'release "
            "charges' to get your money back.",
            "Recovery scams target people who have already been scammed.",
            *all_kinds))
    steps.append(_step(
        "report_nfcc", "follow_up",
        "Also report the incident on the NFCC website listed below, and tell a "
        "trusted family member or friend so you are not handling this alone.",
        "Reports help authorities link cases and warn others.",
        *all_kinds, channel="nfcc"))
    if money:
        steps.append(_step(
            "check_recipient", "follow_up",
            "Optionally check the recipient account yourself on the official Semak Mule portal.",
            "It is a quick way to see whether the account has been reported before; "
            "it does not prove or disprove fraud.",
            "money_sent", channel="semak_mule"))
    return steps


def _clarifying_questions(kinds: dict[str, str]) -> tuple[str, ...]:
    questions: list[str] = []
    unresolved = [k for k, s in kinds.items() if s == "possible"] or (
        ["unspecified_victim"] if "unspecified_victim" in kinds else []
    )
    if not unresolved:
        return ()
    if "money_sent" not in kinds or kinds["money_sent"] == "possible" or "unspecified_victim" in kinds:
        questions.append("Did any money leave your account, and roughly when?")
    if "financial_credentials" not in kinds or kinds["financial_credentials"] == "possible" or "unspecified_victim" in kinds:
        questions.append("Did you share any OTP/TAC, PIN, card details or passwords?")
    if "remote_access" not in kinds and "app_installed" not in kinds:
        questions.append("Did you install an app or give anyone remote access to your device?")
    return tuple(questions[:3])


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def build_incident_plan(
    request: str,
    assessment: Mapping[str, Any] | None = None,
    *,
    prior_incident: bool = False,
    language: str | None = None,
) -> IncidentPlan | None:
    """Return a victim-response plan, or ``None`` if the user reports no incident.

    ``request`` must be the user's own typed text, not OCR text from an
    attachment (attacker-controlled). ``assessment`` is the optional structured
    result of message/URL analysis; it only raises caution. ``prior_incident``
    says an earlier turn in this session already produced a plan, so short
    follow-up answers ("I transferred RM500") are read in that context.
    ``language`` overrides the detected response language ("en", "ms", "zh").
    """
    if not isinstance(request, str) or not request.strip():
        return None
    text = re.sub(r"[^\S\n]+", " ", request).strip()[:_MAX_TEXT_CHARS]

    ctx = _read_assessment(assessment)
    context_ok = prior_incident or ctx.high_risk or has_scam_context(text)
    kinds = detect_signals(text, context_ok)
    if not kinds:
        return None

    # Possible-only incidents become firm when message analysis independently
    # rates the case high/critical; it never reduces anything.
    escalated = ctx.high_risk
    rank = 1
    for kind, status in kinds.items():
        base = _BASE_RANK[kind]
        if kind == "unspecified_victim" and escalated:
            base = 3
        if status == "possible" and not escalated:
            base -= 1
        rank = max(rank, base)
    severity = SEVERITY_ORDER[max(rank, 1) - 1]

    steps = _catalogue(kinds, escalated)
    steps.sort(key=lambda s: _TIER_ORDER[s.tier])  # stable: keeps priority order
    seen: set[str] = set()
    unique = [s for s in steps if not (s.id in seen or seen.add(s.id))]

    channels: list[str] = []
    for s in unique:
        if s.channel and s.channel not in channels:
            channels.append(s.channel)

    top_kind = max(kinds, key=lambda k: (kinds[k] == "confirmed", _BASE_RANK[k]))
    response_language = language if language in SUPPORTED_LANGUAGES else detect_language(text)
    return IncidentPlan(
        severity=severity,
        headline=_HEADLINES[top_kind],
        signals=tuple(Signal(k, s) for k, s in sorted(kinds.items())),
        steps=tuple(unique),
        questions=_clarifying_questions(kinds),
        channels=tuple(channels),
        assessment_used=ctx.used,
        untrusted_contact_seen=bool(_PHONE.search(text) or _URL.search(text)),
        language=response_language,
        headline_kind=top_kind,
    )
