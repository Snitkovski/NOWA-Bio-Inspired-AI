"""Route ``tool_id`` calls to the MCP transport of that ``server_id``.

The host does not branch on product names. READ and WRITE go to the same
router; WRITE still reaches the world only through ApprovalGate.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from nowa_body._compat import ensure_core_src_on_path


class MCPRouter:
    """``server_id`` → ``MCPTransport``. Used as ApprovalGate ``mcp_executor``."""

    def __init__(self, transports: Optional[Dict[str, Any]] = None) -> None:
        self.transports: Dict[str, Any] = dict(transports or {})

    def call_tool(self, tool_id: str, arguments: Optional[dict] = None) -> dict:
        ensure_core_src_on_path()
        from mcp_body.mcp_client import split_tool_id

        server_id, name = split_tool_id(tool_id)
        client = self.transports.get(str(server_id or ""))
        if client is None:
            return {"status": "error", "reason": f"no_transport:{server_id}"}
        try:
            if hasattr(client, "call_tool"):
                result = client.call_tool(name, arguments or {})
            elif hasattr(client, "execute"):
                result = client.execute(tool_id, arguments or {})
            else:
                return {"status": "error", "reason": "transport_not_callable"}
        except Exception as exc:
            return {"status": "error", "reason": f"transport_error:{exc}"}
        if not isinstance(result, dict):
            return {"status": "error", "reason": "non_dict_result", "value": result}
        return result

    def close(self) -> None:
        for client in list(self.transports.values()):
            closer = getattr(client, "close", None)
            if callable(closer):
                try:
                    closer()
                except Exception:
                    continue


__all__ = ["MCPRouter"]
