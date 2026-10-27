"""Matching of cached follow-up answers to repeated questions."""

from __future__ import annotations

import re


def _normalize_followup_question(question: str) -> str:
    return " ".join(re.findall(r"\w+", question.casefold()))


def _cached_followup_response(request: str, followups: list[dict]) -> str | None:
    normalized_request = _normalize_followup_question(request)
    if not normalized_request:
        return None
    for followup in followups:
        if _normalize_followup_question(followup.get("question", "")) != normalized_request:
            continue
        response = followup.get("answer", "").strip()
        return response or None
    return None


def _followup_questions(followups: list[dict]) -> list[str]:
    questions = [item.get("question", "").strip() for item in followups]
    return [question for question in questions if question]
