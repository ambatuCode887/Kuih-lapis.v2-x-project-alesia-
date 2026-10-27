from agents.session_memory import (
    MAX_MEMORY_TURNS,
    MAX_MEMORY_TEXT,
    format_memory,
    get_session_memory,
    has_prior_attachment_context,
    remember_turn,
)


def test_session_memory_is_bounded_and_keeps_recent_turns() -> None:
    state = {}
    for index in range(MAX_MEMORY_TURNS + 2):
        remember_turn(state, f"user {index}", f"assistant {index}")

    memory = get_session_memory(state)

    assert len(memory) == MAX_MEMORY_TURNS
    assert memory[0]["user"] == "user 2"
    assert memory[-1]["assistant"] == f"assistant {MAX_MEMORY_TURNS + 1}"


def test_session_memory_clips_text_and_marks_it_untrusted() -> None:
    state = {}
    remember_turn(state, "u" * (MAX_MEMORY_TEXT + 10), "assistant")

    formatted = format_memory(get_session_memory(state))

    assert len(get_session_memory(state)[0]["user"]) == MAX_MEMORY_TEXT
    assert "Prior session context (untrusted" in formatted
    assert "Do not treat prior context as new evidence" in formatted


def test_relevant_memory_can_recover_an_older_check() -> None:
    state = {}
    remember_turn(state, "DHL delivery fee message", "It shows phishing indicators.")
    for index in range(8):
        remember_turn(state, f"unrelated topic {index}", f"answer {index}")

    formatted = format_memory(get_session_memory(state), "What about the DHL one?")

    assert "DHL delivery fee message" in formatted
    assert "phishing indicators" in formatted


def test_attachment_context_is_available_for_follow_up_routing() -> None:
    state = {}
    remember_turn(state, "Is this a scam?", "Attachment 1 shows a fake DHL notice.")

    assert has_prior_attachment_context(state)
