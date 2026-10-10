"""Re-export platform organ registry (formerly MCPToolRegistry)."""

from ._compat import ensure_core_src_on_path

ensure_core_src_on_path()

from mcp_body.organ_registry import MCPToolRegistry, OrganRegistry  # noqa: E402,F401

__all__ = ["MCPToolRegistry", "OrganRegistry"]
