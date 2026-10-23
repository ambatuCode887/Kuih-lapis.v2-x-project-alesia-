"""Immediate safety notices for explicit high-risk requests."""

from __future__ import annotations

import re


def immediate_safety_notice(request: str) -> str | None:
    """Flag explicit, high-risk requests before slower model analysis starts."""
    normalized = " ".join(re.findall(r"\w+", request.casefold()))
    incoming_request_terms = (
        "someone ask me",
        "someone asked me",
        "someone is asking me",
        "they asked me",
        "asked me to",
        "told me to",
        "wants me to",
        "should i transfer",
        "should i send",
    )
    money_transfer_terms = (
        "transfer money",
        "send money",
        "move money",
        "deposit money",
        "wire money",
        "transfer funds",
        "send funds",
    )
    if any(term in normalized for term in incoming_request_terms) and any(
        term in normalized for term in money_transfer_terms
    ):
        return (
            "Pause before sending money. Independently confirm the request with "
            "your friend through a number or app you already trust, and verify "
            "the recipient account. I'm checking the details now."
        )

    safe_account_terms = (
        "safe account",
        "secure account",
        "protected account",
        "safe bank",
        "secure bank",
        "protected bank",
    )
    transfer_terms = ("transfer", "move", "send", "deposit", "wire")
    if any(term in normalized for term in safe_account_terms) and any(
        term in normalized for term in transfer_terms
    ):
        return (
            "Pause: do not transfer money to a so-called safe or secure account. "
            "Verify with your bank using its official app or a number you find "
            "independently. I'm checking the details now."
        )

    delivery_context = any(
        term in normalized
        for term in ("parcel", "package", "delivery", "shipment", "courier")
    )
    fee_request = any(
        term in normalized
        for term in (
            "delivery fee",
            "shipping fee",
            "parcel fee",
            "additional fee",
            "extra fee",
            "handling fee",
            "customs fee",
            "storage fee",
            "release fee",
        )
    )
    action_requested = any(
        term in normalized for term in ("pay", "click", "link")
    )
    if delivery_context and fee_request and action_requested:
        return (
            "Pause: don't click the message link or pay the extra delivery fee "
            "yet. I can't verify the sender or charge from this description. "
            "Check the tracking and any fee directly in the courier's official "
            "app or website, or contact it using details you find independently. "
            "This caution is not a confirmed fraud verdict."
        )

    sensitive_terms = (
        "password",
        "passcode",
        "one time code",
        "verification code",
        "otp",
    )
    request_terms = (
        "asks me to",
        "asked me to",
        "asking me to",
        "asks you to",
        "asked you to",
        "asking you to",
        "reply with",
        "send your",
        "share your",
        "provide your",
        "enter your",
    )
    if any(term in normalized for term in sensitive_terms) and any(
        term in normalized for term in request_terms
    ):
        return (
            "Pause: do not share a password, passcode, or one-time code. "
            "Verify the request through the service's official channel. "
            "I'm checking the details now."
        )

    if "remote access" in normalized and any(
        term in normalized for term in ("asks me to", "asked me to", "asking me to", "give them")
    ):
        return (
            "Pause: do not grant remote access to an unsolicited caller. "
            "Contact the organization through an official channel. "
            "I'm checking the details now."
        )

    return None
