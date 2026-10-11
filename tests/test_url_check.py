from agents.tools.agents.url_check.agent import VT_READ_ONLY_TOOLS, url_check_agent


def test_url_check_agent_is_read_only():
    agent = url_check_agent()
    assert agent.name == "url_check_agent"
    assert set(VT_READ_ONLY_TOOLS) == {"get_domain_report", "get_url_report", "get_ip_report"}
    assert sum(type(t).__name__ == "McpToolset" for t in agent.tools) == 1
    assert "Never submit" in agent.instruction


def test_url_check_routes_to_coordinator():
    agent = url_check_agent()
    assert [a.name for a in agent.sub_agents] == ["coordinator_agent"]


def test_url_check_registered_on_root_agent():
    from agents.agent import root_agent

    assert "url_check_agent" in [a.name for a in root_agent.sub_agents]

