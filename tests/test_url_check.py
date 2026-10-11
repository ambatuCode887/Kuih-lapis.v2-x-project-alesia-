from agents.tools.agents.url_check.agent import VT_READ_ONLY_TOOLS, url_check_agent


def test_url_check_agent_is_read_only():
    agent = url_check_agent()
    assert agent.name == "url_check_agent"
    assert set(VT_READ_ONLY_TOOLS) == {"get_domain_report", "get_url_report", "get_ip_report"}
    assert len(agent.tools) == 1
    assert "Never submit" in agent.instruction


def test_url_check_registered_on_coordinator():
    from agents.tools.agents.coordinator_agents.agent import coordinator_agent

    assert "url_check_agent" in [a.name for a in coordinator_agent().sub_agents]

