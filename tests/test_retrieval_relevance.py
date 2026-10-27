from agents.tools.agents.retrieval.agent import _retrieval_matches_query


def test_unrelated_retrieval_hit_is_not_used_as_answer() -> None:
    results = [{"text": "Phishing attacks use deceptive messages and links."}]

    assert not _retrieval_matches_query("What is a backdoor attack?", results)


def test_on_topic_retrieval_hit_is_kept() -> None:
    results = [{"text": "A backdoor attack creates unauthorized access."}]

    assert _retrieval_matches_query("What is a backdoor attack?", results)
