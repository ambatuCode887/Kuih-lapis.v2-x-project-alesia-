from pathlib import Path

from google.genai import types
from google.adk.agents.llm_agent import Agent

from agents.config import agent_model
from agents.tools.functions.retrieve.credential_stuffing import retrieve_knowledge

_PROMPT = Path(__file__).with_name("prompt.md")


def _reset_retrieval_state(callback_context) -> None:
    callback_context.state["retrieval_tool_called"] = False


def _require_retrieval_tool(callback_context, llm_request) -> None:
    called = callback_context.state.get("retrieval_tool_called", False)
    llm_request.config.tool_config = types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="AUTO" if called else "ANY",
            allowed_function_names=None if called else ["retrieve_knowledge"],
        )
    )


def _mark_retrieval_tool_called(tool, args, tool_context, tool_response) -> None:
    if getattr(tool, "name", None) == "retrieve_knowledge":
        tool_context.state["retrieval_tool_called"] = True


def retrieval_agent() -> Agent:
    """Factory function to create a retrieval agent."""
    return Agent(
        model=agent_model(),
        name="retrieval_agent",
        description="Answers cybersecurity knowledge questions using Qdrant evidence.",
        instruction=_PROMPT.read_text(encoding="utf-8"),
        tools=[retrieve_knowledge],
        mode="single_turn",
        before_agent_callback=_reset_retrieval_state,
        before_model_callback=_require_retrieval_tool,
        after_tool_callback=_mark_retrieval_tool_called,
    )
