"""Tests for MockMCPClient / MockMCPTool (spec §8)."""

from nowa_body.mock_mcp import MockMCPClient, MockMCPTool


def test_execute_unknown_tool_returns_error_status():
    client = MockMCPClient()
    result = client.execute("nope", {"a": 1})
    assert result["status"] == "error"
    assert "unknown_tool:nope" in result["reason"]


def test_call_log_records_params():
    client = MockMCPClient()
    tool = MockMCPTool("echo", lambda p: {"status": "ok", **p})
    client.register(tool)
    assert client.execute("echo", {"k": "v"})["k"] == "v"
    assert tool.call_log == [{"k": "v"}]


def test_tool_exception_becomes_error_result():
    def boom(_params):
        raise ValueError("x")

    client = MockMCPClient()
    client.register(MockMCPTool("boom", boom))
    result = client.execute("boom", {})
    assert result["status"] == "error"
    assert "tool_error" in result["reason"]
