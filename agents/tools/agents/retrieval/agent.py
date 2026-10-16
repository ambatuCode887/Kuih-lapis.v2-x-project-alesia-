import asyncio
import re

from google.genai import types
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from agents.tools.functions.retrieve.credential_stuffing import format_passage, retrieve_knowledge

_QA_RECORD = re.compile(
    r"\s*Question:\s*(?P<question>.*?)\s*\nAnswer:\s*(?P<answer>.*?)\s*\Z",
    re.IGNORECASE | re.DOTALL,
)


def _cached_followups(results: list[dict], query: str) -> list[dict[str, str]]:
    normalized_query = " ".join(query.casefold().split())
    followups = []
    seen_questions = {normalized_query}
    for result in results:
        match = _QA_RECORD.fullmatch(str(result.get("text", "")))
        if not match:
            continue
        question = match.group("question").strip()
        answer = match.group("answer").strip()
        normalized_question = " ".join(question.casefold().split())
        if not question or not answer or normalized_question in seen_questions:
            continue
        seen_questions.add(normalized_question)
        followups.append(
            {
                "question": question,
                "answer": answer,
                "source": str(result.get("source", "")),
                "chunk_index": str(result.get("chunk_index", "")),
            }
        )
        if len(followups) == 3:
            break
    return followups


class RetrievalAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        content = ctx.user_content
        query = "\n".join(
            part.text
            for part in (content.parts if content else [])
            if getattr(part, "text", None)
            and "[BEGIN UNTRUSTED ATTACHMENT DATA" not in part.text
            and "[Extracted attachment text;" not in part.text
        ).strip()

        followups = []
        if not query:
            report = "No query text was provided, so no knowledge search was run."
        else:
            retrieval = await asyncio.to_thread(retrieve_knowledge, query)
            results = retrieval.get("results", [])
            followups = _cached_followups(results, query)
            if not results:
                report = "No relevant context was found in the knowledge base."
            else:
                passages = [format_passage(index, result) for index, result in enumerate(results, start=1)]
                report = "Retrieved evidence:\n" + "\n\n".join(passages)

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(
                role="model",
                parts=[types.Part(text=report)],
            ),
            actions=EventActions(state_delta={"cached_followups": followups}),
            turn_complete=True,
        )


def retrieval_agent() -> BaseAgent:
    """Factory function to create a retrieval agent."""
    return RetrievalAgent(
        name="retrieval_agent",
        description="Answers cybersecurity knowledge questions using Qdrant evidence.",
    )
