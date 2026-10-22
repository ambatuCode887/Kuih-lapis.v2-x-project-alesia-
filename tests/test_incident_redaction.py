"""Redaction tests use obviously fake values only."""

from agents.tools.functions.incident.redaction import redact


def test_redacts_common_identifiers():
    text = (
        "IC 900101-14-5678, phone +60 12-345 6789, mail a.b@example.com, "
        "card 4111 1111 1111 1111, acct 1234567890123, OTP is 482913."
    )
    result = redact(text)
    for leaked in ("900101", "345 6789", "a.b@example.com", "4111", "1234567890123", "482913"):
        assert leaked not in result.text
    assert {"nric", "phone", "email", "card_number", "account_number", "otp"} <= set(result.counts)


def test_redacts_secrets():
    text = "token=abc123secret key sk-" + "A" * 24 + " https://user:hunter2@host.example/x"
    result = redact(text)
    assert "abc123secret" not in result.text
    assert "hunter2" not in result.text
    assert "sk-" + "A" * 24 not in result.text


def test_redacts_private_key_block():
    pem = "-----BEGIN PRIVATE KEY-----\nMIIFAKE\n-----END PRIVATE KEY-----"
    assert "MIIFAKE" not in redact("x " + pem).text


def test_keeps_non_sensitive_text_and_amounts():
    result = redact("I transferred RM3000 yesterday.")
    assert result.text == "I transferred RM3000 yesterday."
    assert result.total == 0


def test_non_luhn_long_number_is_not_marked_as_card():
    assert "card_number" not in redact("ref 1234 5678 9012 3456").counts


def test_empty_and_idempotent():
    assert redact("").text == ""
    once = redact("mail me at a@example.com").text
    assert redact(once).text == once
