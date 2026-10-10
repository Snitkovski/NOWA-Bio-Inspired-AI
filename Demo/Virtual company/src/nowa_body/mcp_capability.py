"""Re-export platform MCP organ types so Demo hosts keep ``nowa_body`` imports."""

from ._compat import ensure_core_src_on_path

ensure_core_src_on_path()

from mcp_body.mcp_capability import CapabilityRisk, MCPCapability, parse_risk  # noqa: E402,F401

__all__ = ["CapabilityRisk", "MCPCapability", "parse_risk"]
