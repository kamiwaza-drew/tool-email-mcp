"""Tests for FastMCP server."""

import pytest
from starlette.testclient import TestClient
from tool_email_mcp.server import app, mcp


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_endpoint(self, client):
        """Health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "provider_configured" in data
        assert "security_enabled" in data
        assert data["security_enabled"] is True


class TestToolRegistration:
    """Tests for MCP tool registration."""

    def test_all_tools_registered(self):
        """All 10 tools are registered."""
        tool_names = [tool.name for tool in mcp.list_tools()]

        expected_tools = [
            "configure_email_provider",
            "list_emails",
            "read_email",
            "search_emails",
            "get_folders",
            "send_email",
            "reply_email",
            "forward_email",
            "delete_email",
            "mark_email_read",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    def test_tool_count(self):
        """Exactly 10 tools registered."""
        tools = mcp.list_tools()
        assert len(tools) == 10

    def test_tool_descriptions(self):
        """All tools have descriptions."""
        tools = mcp.list_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} missing description"
            assert len(tool.description) > 10, f"Tool {tool.name} has short description"

    def test_security_annotations(self):
        """Tools have security documentation."""
        tools = mcp.list_tools()
        for tool in tools:
            # Check that description mentions security
            desc = tool.description.lower()
            # Most tools should mention some security aspect
            if tool.name != "get_folders":  # get_folders is metadata only
                assert any(
                    word in desc
                    for word in ["security", "validate", "oauth", "sanitize", "prevent"]
                ), f"Tool {tool.name} missing security documentation"
