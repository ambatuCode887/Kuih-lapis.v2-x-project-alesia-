from pathlib import Path

from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

from agents.config import agent_model, required_env
from agents.tools.agents.message_agents.attachments import isolate_current_turn

PROMPT_PATH = Path(__file__).with_name("prompt.md")

VT_MCP_URL = "https://ai.virustotal.com/mcp"

# Read-only lookups; submission tools are excluded so no URL/file is shared without consent.
VT_READ_ONLY_TOOLS = ["get_domain_report", "get_url_report", "get_ip_report"]


def virustotal_toolset() -> McpToolset:
    """Connect to VirusTotal's hosted MCP server using a VTAI token."""
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=VT_MCP_URL,
            headers={"Authorization": f"Bearer {required_env('VTAI_TOKEN')}"},
            timeout=30,
        ),
        tool_filter=VT_READ_ONLY_TOOLS,
    )


def url_check_agent() -> Agent:
    """Factory function to create the URL/domain reputation agent."""
    return Agent(
        model=agent_model(),
        name="url_check_agent",
        description=(
            "Checks domain, URL and IP reputation using VirusTotal threat "
            "intelligence and returns a structured verdict."
        ),
        instruction=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=[virustotal_toolset()],
        mode="single_turn",
        before_model_callback=isolate_current_turn,
    )
