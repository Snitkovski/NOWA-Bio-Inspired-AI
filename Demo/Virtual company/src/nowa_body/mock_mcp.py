"""Deterministic MCP stand-in for tests — no network, no real servers."""

from __future__ import annotations

from typing import Callable, Dict, List


class MockMCPTool:
    """One fake tool: deterministic responses for tests, keyed by ``response_fn``."""

    def __init__(self, tool_id: str, response_fn: Callable[[dict], dict]) -> None:
        self.tool_id = tool_id
        self.response_fn = response_fn
        self.call_log: List[dict] = []

    def __call__(self, params: dict) -> dict:
        self.call_log.append(dict(params or {}))
        return self.response_fn(params or {})


class MockMCPClient:
    """Dispatches by tool_id. This is the ``mcp_executor`` ApprovalGate expects."""

    def __init__(self) -> None:
        self.tools: Dict[str, MockMCPTool] = {}

    def register(self, tool: MockMCPTool) -> None:
        self.tools[tool.tool_id] = tool

    def execute(self, tool_id: str, params: dict) -> dict:
        tool = self.tools.get(tool_id)
        if tool is None:
            return {"status": "error", "reason": f"unknown_tool:{tool_id}"}
        try:
            result = tool(params or {})
        except TimeoutError as exc:
            return {"status": "error", "reason": f"timeout:{exc}"}
        except Exception as exc:
            return {"status": "error", "reason": f"tool_error:{exc}"}
        if not isinstance(result, dict):
            return {"status": "error", "reason": "non_dict_result", "value": result}
        return result

    def list_tools(self) -> list:
        """MCPTransport.list_tools — descriptors for discovery."""
        from nowa_body._compat import ensure_core_src_on_path

        ensure_core_src_on_path()
        from mcp_body.mcp_client import MCPToolDescriptor, split_tool_id

        descriptors = []
        for tool_id, tool in self.tools.items():
            _server, name = split_tool_id(tool_id)
            descriptors.append(
                MCPToolDescriptor(
                    name=name or tool_id,
                    description=str(getattr(tool, "description", "") or name or tool_id),
                    input_schema=dict(getattr(tool, "input_schema", {}) or {}),
                )
            )
        return descriptors

    def call_tool(self, name: str, arguments: dict) -> dict:
        """MCPTransport.call_tool — resolve by leaf name or full tool_id."""
        key = str(name or "")
        if key in self.tools:
            return self.execute(key, arguments or {})
        for tool_id in self.tools:
            if tool_id.endswith(f"__{key}") or tool_id == key:
                return self.execute(tool_id, arguments or {})
        return {"status": "error", "reason": f"unknown_tool:{name}"}
