import pytest

from agents.agent import (
    _GIBBERISH_REPLY,
    _OFF_TOPIC_REPLY,
    _is_gibberish,
    _unsupported_request_reply,
)


def test_keyboard_mash_is_gibberish():
    assert _is_gibberish("asdkjh qwrtzxc zzxvbnm")


def test_numbers_only_are_gibberish():
    assert _is_gibberish("12345")


def test_normal_question_is_not_gibberish():
    assert not _is_gibberish("How do I protect myself from phishing emails?")


def test_non_ascii_question_is_not_gibberish():
    assert not _is_gibberish("什么是网络钓鱼？")


def test_gibberish_is_refused():
    reply = _unsupported_request_reply("asdkjh qwrtzxc zzxvbnm", attachment_present=False, state={})
    assert reply == _GIBBERISH_REPLY


def test_off_topic_question_is_refused():
    reply = _unsupported_request_reply(
        "What is the capital of France?", attachment_present=False, state={}
    )
    assert reply == _OFF_TOPIC_REPLY


def test_cyber_question_passes_gate():
    reply = _unsupported_request_reply("What is SQL injection?", attachment_present=False, state={})
    assert reply is None


@pytest.mark.parametrize(
    "question",
    [
        "What is credential stuffing?",
        "How do I dispose of sensitive documents?",
        "What is ransomware?",
        "How do I secure a Kubernetes cluster?",
        "Is my home router safe?",
    ],
)
def test_legitimate_security_questions_pass_gate(question):
    assert _unsupported_request_reply(question, attachment_present=False, state={}) is None


def test_follow_up_after_knowledge_question_passes_gate():
    reply = _unsupported_request_reply(
        "What about that?",
        attachment_present=False,
        state={"knowledge_memory": ["How do I stop phishing?"]},
    )
    assert reply is None


def test_gibberish_is_refused_even_with_memory():
    reply = _unsupported_request_reply(
        "asdkjh qwrtzxc zzxvbnm",
        attachment_present=False,
        state={"knowledge_memory": ["How do I stop phishing?"]},
    )
    assert reply == _GIBBERISH_REPLY


def test_attachment_and_url_skip_gate():
    off_topic = "What is the capital of France?"
    assert _unsupported_request_reply(off_topic, attachment_present=True, state={}) is None
    assert (
        _unsupported_request_reply(
            "Is https://example.com safe?", attachment_present=False, state={}
        )
        is None
    )
